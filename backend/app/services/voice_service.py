"""
voice_service.py — ACS Call Automation + Azure Voice Live API bridge.

Unique feature: per-call transcript accumulation.
On CallDisconnected, the transcript is retrieved from get_and_clear_transcript()
and classified via GPT to auto-create a maintenance/security ticket.
"""
from __future__ import annotations

import asyncio
import json
import logging

import requests as http_requests
import websockets
from azure.communication.callautomation import (
    AudioFormat,
    CallAutomationClient,
    MediaStreamingAudioChannelType,
    MediaStreamingContentType,
    MediaStreamingOptions,
    PhoneNumberIdentifier,
    StreamingTransportType,
)
from openai import AzureOpenAI

from app.auth import get_credential, get_openai_token_provider
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the society support assistant for a residential community. "
    "Help residents raise maintenance and security complaints. "
    "Keep ALL responses under 2 sentences. Ask one question at a time. "
    "Do not use filler phrases. Be concise and helpful."
)

CLASSIFY_PROMPT = """You are a complaint classifier for a residential society helpdesk.
Given a call transcript, extract a JSON object with these fields:
- category: one of gate_security, lift, plumbing, electrical, parking, housekeeping, noise, maintenance, emergency, general
- sub_category: short string (e.g. "water leak", "power outage")
- priority: low, medium, high, or emergency
- location: tower/floor/flat if mentioned, else ""
- description: clean 1-2 sentence summary of the complaint
Respond ONLY with the JSON object. No explanation."""

# Per-call transcript: call_connection_id → list of "Role: text" lines
_transcripts: dict[str, list[str]] = {}

# Queue of answer-call IDs waiting for a WebSocket to connect.
# Each answer_call enqueues its call_connection_id; the next WS connect dequeues it.
_pending_call_ids: list[str] = []

_call_client: CallAutomationClient | None = None
_oai_client: AzureOpenAI | None = None

# Cached Foundry agent config (fetched once at first call)
_agent_config: dict | None = None


def _fetch_agent_config() -> dict:
    """Fetch agent instructions and voice-live config from Foundry.

    Returns dict with 'instructions', 'voice_live_session' keys.
    """
    global _agent_config
    if _agent_config is not None:
        return _agent_config

    project = settings.foundry_project_endpoint.rstrip("/")
    agent = settings.foundry_agent_name
    url = f"{project}/agents/{agent}?api-version=2025-05-15-preview"

    token = get_credential().get_token("https://ai.azure.com/.default")
    headers = {"Authorization": f"Bearer {token.token}"}

    try:
        resp = http_requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        latest = data.get("versions", {}).get("latest", {})
        defn = latest.get("definition", {})
        meta = latest.get("metadata", {})

        instructions = defn.get("instructions", "")
        vl_raw = meta.get("microsoft.voice-live.configuration", "{}")
        vl_session = json.loads(vl_raw).get("session", {})

        _agent_config = {
            "instructions": instructions,
            "voice_live_session": vl_session,
        }
        logger.info(
            "Fetched Foundry agent config: agent=%s instructions_len=%d voice=%s",
            agent, len(instructions),
            vl_session.get("voice", {}).get("name", "default"),
        )
    except Exception:
        logger.exception("Failed to fetch Foundry agent config — using defaults")
        _agent_config = {"instructions": "", "voice_live_session": {}}

    return _agent_config


def _get_call_client() -> CallAutomationClient:
    global _call_client
    if _call_client is None:
        _call_client = CallAutomationClient.from_connection_string(settings.acs_connection_string)
    return _call_client


def _get_oai_client() -> AzureOpenAI:
    global _oai_client
    if _oai_client is None:
        _oai_client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_ad_token_provider=get_openai_token_provider(),
            api_version="2024-12-01-preview",
        )
    return _oai_client


def answer_call(incoming_call_context: str, callback_uri: str, websocket_url: str) -> str:
    """Answer an incoming call with bidirectional media streaming and init transcript store."""
    media_streaming = MediaStreamingOptions(
        transport_url=websocket_url,
        transport_type=StreamingTransportType.WEBSOCKET,
        content_type=MediaStreamingContentType.AUDIO,
        audio_channel_type=MediaStreamingAudioChannelType.MIXED,
        start_media_streaming=True,
        enable_bidirectional=True,
        audio_format=AudioFormat.PCM24_K_MONO,
    )
    result = _get_call_client().answer_call(
        incoming_call_context=incoming_call_context,
        callback_url=callback_uri,
        media_streaming=media_streaming,
    )
    call_id = result.call_connection_id
    _transcripts[call_id] = []
    _pending_call_ids.append(call_id)
    logger.info("Answered call: %s", call_id)
    return call_id


def place_outbound_call(target_phone: str) -> str:
    """Place an outbound call to target_phone with media streaming."""
    host = settings.callback_host
    callback_uri = f"{host}/api/call-events"
    ws_url = host.replace("https://", "wss://").replace("http://", "ws://")

    media_streaming = MediaStreamingOptions(
        transport_url=f"{ws_url}/ws/media",
        transport_type=StreamingTransportType.WEBSOCKET,
        content_type=MediaStreamingContentType.AUDIO,
        audio_channel_type=MediaStreamingAudioChannelType.MIXED,
        start_media_streaming=True,
        enable_bidirectional=True,
        audio_format=AudioFormat.PCM24_K_MONO,
    )

    source_phone = PhoneNumberIdentifier(settings.acs_phone_number)
    target = PhoneNumberIdentifier(target_phone)

    result = _get_call_client().create_call(
        target_participant=target,
        source_caller_id_number=source_phone,
        callback_url=callback_uri,
        media_streaming=media_streaming,
    )

    call_id = result.call_connection_id
    _transcripts[call_id] = []
    _pending_call_ids.append(call_id)
    logger.info("Placed outbound call to %s: call_id=%s", target_phone, call_id)
    return call_id


def resolve_call_id(ws_subscription_id: str) -> str:
    """Map a WebSocket subscription ID to the answer-call connection ID.

    ACS uses a different subscriptionId on the media WebSocket than the
    callConnectionId returned by answer_call().  Because answer_call()
    always fires before the WS connects, we simply dequeue the first
    pending call ID.
    """
    if _pending_call_ids:
        call_id = _pending_call_ids.pop(0)
        logger.info(
            "Resolved ws_subscription=%s → call=%s", ws_subscription_id, call_id
        )
        return call_id
    # Fallback: use the subscription ID itself (no mapping available).
    logger.warning(
        "No pending call ID for ws_subscription=%s — using it as-is",
        ws_subscription_id,
    )
    return ws_subscription_id


def get_and_clear_transcript(call_id: str) -> str:
    """Return the full accumulated transcript for a call, then remove it from memory."""
    lines = _transcripts.pop(call_id, [])
    return "\n".join(lines)


def classify_transcript(transcript: str) -> dict:
    """Use GPT to extract structured complaint fields from a call transcript."""
    if not transcript.strip():
        return {}
    try:
        response = _get_oai_client().chat.completions.create(
            model=settings.azure_openai_chat_deployment,
            messages=[
                {"role": "system", "content": CLASSIFY_PROMPT},
                {"role": "user", "content": transcript},
            ],
            temperature=0,
            max_tokens=300,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception:
        logger.exception("Transcript classification failed")
        return {}


async def handle_media_websocket(acs_ws, call_id: str) -> None:
    """
    Bridge audio between ACS WebSocket and Voice Live API.
    Accumulates ASR/TTS transcripts per call_id for later ticket creation.
    """
    # Build the Voice Live WebSocket URL (no &agent= — we inject config ourselves)
    endpoint = settings.cognitive_services_endpoint.rstrip("/")
    vl_url = (
        f"{endpoint}/voice-live/realtime"
        f"?api-version=2025-05-01-preview&model={settings.voice_live_model}"
    )
    vl_url = vl_url.replace("https://", "wss://")

    token = get_credential().get_token("https://cognitiveservices.azure.com/.default")
    headers = {"Authorization": f"Bearer {token.token}"}

    logger.info("Connecting to Voice Live: %s", vl_url)

    async with websockets.connect(vl_url, additional_headers=headers) as vl_ws:
        logger.info("Voice Live connected  call=%s", call_id)

        # Build session.update from Foundry agent config or local defaults
        if settings.foundry_agent_name and settings.foundry_project_endpoint:
            agent_cfg = _fetch_agent_config()
            vl_session = agent_cfg.get("voice_live_session", {})

            session_config: dict = {}

            # Instructions from agent definition
            if agent_cfg.get("instructions"):
                session_config["instructions"] = agent_cfg["instructions"]
            else:
                session_config["instructions"] = SYSTEM_PROMPT

            # Voice from voice-live metadata
            voice_cfg = vl_session.get("voice")
            if voice_cfg:
                session_config["voice"] = {
                    k: v for k, v in voice_cfg.items() if v is not None
                }

            # Turn detection
            td = vl_session.get("turnDetection")
            if td:
                session_config["turn_detection"] = {
                    k: v for k, v in {
                        "type": td.get("type", "azure_semantic_vad"),
                        "remove_filler_words": td.get("removeFillerWords", False),
                    }.items() if v is not None
                }
            else:
                session_config["turn_detection"] = {
                    "type": "azure_semantic_vad",
                    "threshold": 0.3,
                    "prefix_padding_ms": 200,
                    "silence_duration_ms": 200,
                    "remove_filler_words": False,
                }

            # Audio transcription
            transcription = vl_session.get("inputAudioTranscription")
            if transcription:
                session_config["input_audio_transcription"] = transcription

            # Noise reduction / echo cancellation (use from agent or defaults)
            nr = vl_session.get("inputAudioNoiseReduction")
            session_config["input_audio_noise_reduction"] = (
                nr if nr else {"type": "azure_deep_noise_suppression"}
            )
            ec = vl_session.get("inputAudioEchoCancellation")
            session_config["input_audio_echo_cancellation"] = (
                ec if ec else {"type": "server_echo_cancellation"}
            )

            logger.info("Using Foundry agent config: voice=%s", voice_cfg)
        else:
            # No Foundry agent — use local instructions and voice
            session_config = {
                "instructions": SYSTEM_PROMPT,
                "turn_detection": {
                    "type": "azure_semantic_vad",
                    "threshold": 0.3,
                    "prefix_padding_ms": 200,
                    "silence_duration_ms": 200,
                    "remove_filler_words": False,
                },
                "input_audio_noise_reduction": {"type": "azure_deep_noise_suppression"},
                "input_audio_echo_cancellation": {"type": "server_echo_cancellation"},
                "voice": {
                    "name": "en-US-Aria:DragonHDLatestNeural",
                    "type": "azure-standard",
                    "temperature": 0.8,
                },
            }

        await vl_ws.send(json.dumps({"type": "session.update", "session": session_config}))
        await vl_ws.send(json.dumps({"type": "response.create"}))

        async def acs_to_vl():
            """Forward caller audio: ACS → Voice Live."""
            while True:
                try:
                    raw = await acs_ws.receive_text()
                    data = json.loads(raw)
                    if data.get("kind") == "AudioData":
                        audio_data = data.get("audioData", {})
                        if not audio_data.get("silent", True):
                            b64 = audio_data.get("data", "")
                            if b64:
                                await vl_ws.send(json.dumps({
                                    "type": "input_audio_buffer.append",
                                    "audio": b64,
                                }))
                except Exception:
                    break

        async def vl_to_acs():
            """Forward TTS audio: Voice Live → ACS, and accumulate transcript."""
            async for message in vl_ws:
                try:
                    event = json.loads(message)
                    etype = event.get("type", "")

                    if etype == "response.audio.delta":
                        delta = event.get("delta", "")
                        if delta:
                            await acs_ws.send_text(json.dumps({
                                "Kind": "AudioData",
                                "AudioData": {"Data": delta},
                                "StopAudio": None,
                            }))

                    elif etype == "input_audio_buffer.speech_started":
                        # Caller started speaking — stop current TTS playback
                        await acs_ws.send_text(json.dumps({
                            "Kind": "StopAudio",
                            "AudioData": None,
                            "StopAudio": {},
                        }))

                    elif etype == "response.audio_transcript.done":
                        text = event.get("transcript", "")
                        if text:
                            logger.info("Agent: %s", text)
                            if call_id in _transcripts:
                                _transcripts[call_id].append(f"Agent: {text}")

                    elif etype == "conversation.item.input_audio_transcription.completed":
                        text = event.get("transcript", "")
                        if text:
                            logger.info("Resident: %s", text)
                            if call_id in _transcripts:
                                _transcripts[call_id].append(f"Resident: {text}")

                    elif etype == "error":
                        logger.error("Voice Live error: %s", event)

                except Exception as exc:
                    logger.warning("vl_to_acs error: %s", exc)

        await asyncio.gather(acs_to_vl(), vl_to_acs())
