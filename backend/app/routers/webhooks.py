"""
webhooks.py — ACS EventGrid events + WebSocket media bridge.

Endpoints:
  POST /api/incoming-call   — ACS IncomingCall event (EventGrid)
  POST /api/call-events     — ACS call-state callbacks
  WS   /ws/media            — Bidirectional audio bridge (ACS ↔ Voice Live)

On CallDisconnected the accumulated transcript is sent to GPT and the
extracted complaint fields are persisted as a ticket automatically.
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import Channel, ComplaintCreate, Priority, TicketCategory
from app.services import ticket_service, voice_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Maps ACS call_connection_id → caller E.164 phone number
_call_to_caller: dict[str, str] = {}


# ── EventGrid handshake helper ───────────────────────────────────────────────

def _validation_code(events: list) -> str | None:
    for ev in events:
        if ev.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
            return ev["data"]["validationCode"]
    return None


# ── POST /api/incoming-call ──────────────────────────────────────────────────

@router.post("/api/incoming-call")
async def incoming_call(request: Request):
    """Handle ACS IncomingCall EventGrid event — answer with media streaming."""
    body = await request.json()
    events = body if isinstance(body, list) else [body]

    code = _validation_code(events)
    if code:
        return JSONResponse({"validationResponse": code})

    for event in events:
        if event.get("eventType") != "Microsoft.Communication.IncomingCall":
            continue
        data = event.get("data", {})
        incoming_call_context = data.get("incomingCallContext", "")
        if not incoming_call_context:
            continue

        caller_phone = ""
        try:
            from_info = data.get("from", {})
            caller_phone = (
                from_info["phoneNumber"]["value"]
                if from_info.get("kind") == "phoneNumber"
                else from_info.get("rawId", "")
            )
        except Exception:
            pass
        logger.info("Incoming call from: %s", caller_phone)

        host = settings.callback_host
        callback_uri = f"{host}/api/call-events"
        ws_url = host.replace("https://", "wss://").replace("http://", "ws://")

        try:
            # First get the call_id, then build WS URL with it as query param
            # so the WebSocket handler uses the SAME ID as CallDisconnected.
            call_id = voice_service.answer_call(
                incoming_call_context, callback_uri,
                f"{ws_url}/ws/media",
            )
            _call_to_caller[call_id] = caller_phone
        except Exception:
            logger.exception("answer_call failed")

    return Response(status_code=200)


# ── POST /api/call-events ────────────────────────────────────────────────────

@router.post("/api/call-events")
async def call_events(request: Request, background_tasks: BackgroundTasks):
    """Handle ACS Call Automation callbacks. On disconnect, auto-create ticket."""
    body = await request.json()
    events = body if isinstance(body, list) else [body]

    for event in events:
        event_type = event.get("type", event.get("eventType", ""))
        data = event.get("data", event)
        call_id = data.get("callConnectionId", "")
        logger.info("Call event: %s  call=%s", event_type, call_id)

        if "MediaStreamingStarted" in event_type:
            update = data.get("mediaStreamingUpdate", {})
            logger.info("Media streaming started: status=%s", update.get("mediaStreamingStatus"))

        elif "MediaStreamingFailed" in event_type:
            result_info = data.get("resultInformation", {})
            logger.error(
                "Media streaming failed: code=%s msg=%s",
                result_info.get("code"), result_info.get("message"),
            )

        elif "CallDisconnected" in event_type and call_id:
            caller_phone = _call_to_caller.pop(call_id, "")
            logger.info("Call disconnected: %s  caller=%s", call_id, caller_phone)
            background_tasks.add_task(_create_ticket_from_call, call_id, caller_phone)

    return Response(status_code=200)


# ── Background task: transcript → ticket ────────────────────────────────────

async def _create_ticket_from_call(call_id: str, caller_phone: str) -> None:
    """
    Retrieve the accumulated call transcript, run GPT classification,
    and persist it as a structured complaint ticket.
    """
    transcript = voice_service.get_and_clear_transcript(call_id)
    if not transcript.strip():
        logger.info("No transcript for call %s — skipping ticket creation", call_id)
        return

    logger.info(
        "Creating ticket from call %s  transcript_length=%d chars",
        call_id, len(transcript),
    )

    loop = asyncio.get_event_loop()
    fields = await loop.run_in_executor(None, voice_service.classify_transcript, transcript)

    complaint = ComplaintCreate(
        channel=Channel.voice,
        caller_phone=caller_phone,
        category=fields.get("category", TicketCategory.general),
        sub_category=fields.get("sub_category", ""),
        priority=fields.get("priority", Priority.medium),
        location=fields.get("location", ""),
        description=fields.get("description", transcript[:500] if not fields else ""),
        transcript=transcript,
        source_call_id=call_id,
    )

    ticket = ticket_service.create_ticket(complaint)
    logger.info(
        "Auto-created ticket %s  call=%s  category=%s  priority=%s",
        ticket.id, call_id, ticket.category, ticket.priority,
    )


# ── WebSocket /ws/media — ACS ↔ Voice Live bridge ───────────────────────────

@router.websocket("/ws/media")
async def media_websocket(websocket: WebSocket):
    """Bidirectional audio bridge. Reads call_id from first AudioMetadata frame."""
    await websocket.accept()

    # Read the first frame (AudioMetadata) — we need the subscriptionId to
    # find the matching answer-call-ID via the mapping in voice_service.
    ws_subscription_id = ""
    try:
        first_raw = await websocket.receive_text()
        first = json.loads(first_raw)
        if first.get("kind") == "AudioMetadata":
            ws_subscription_id = first.get("audioMetadata", {}).get("subscriptionId", "")
    except Exception:
        pass

    # Resolve to the answer-call-ID (the one used by CallDisconnected).
    call_id = voice_service.resolve_call_id(ws_subscription_id)
    logger.info(
        "ACS media WebSocket connected  ws_sub=%s  call=%s",
        ws_subscription_id, call_id,
    )
    try:
        await voice_service.handle_media_websocket(websocket, call_id)
    except WebSocketDisconnect:
        logger.info("ACS media WebSocket disconnected  call=%s", call_id)
    except Exception:
        logger.exception("Media WebSocket error  call=%s", call_id)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
