"""
health.py — Service health checks for the App Health dashboard.

GET /api/health/services → returns status of all dependent services.
"""
from __future__ import annotations

import asyncio
import logging
from functools import partial

import requests as http_requests
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.auth import get_credential
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _check_backend() -> dict:
    return {"name": "Backend API", "status": "healthy", "detail": "Running"}


def _check_devtunnel() -> dict:
    """Ping the public callback host /health endpoint."""
    url = settings.callback_host.rstrip("/")
    if not url:
        return {"name": "Dev Tunnel", "status": "unknown", "detail": "CALLBACK_HOST not set"}
    try:
        resp = http_requests.get(f"{url}/health", timeout=5)
        if resp.status_code == 200:
            return {"name": "Dev Tunnel", "status": "healthy", "detail": url}
        return {"name": "Dev Tunnel", "status": "unhealthy", "detail": f"HTTP {resp.status_code}"}
    except Exception:
        return {"name": "Dev Tunnel", "status": "unhealthy", "detail": "Connection failed"}


def _check_cognitive_services() -> dict:
    """Check if the Cognitive Services / Voice Live endpoint is reachable."""
    endpoint = settings.cognitive_services_endpoint.rstrip("/")
    if not endpoint:
        return {"name": "Voice Live API", "status": "unknown", "detail": "COGNITIVE_SERVICES_ENDPOINT not set"}
    try:
        # Hit the OpenAI models list endpoint as a lightweight auth check
        token = get_credential().get_token("https://cognitiveservices.azure.com/.default")
        resp = http_requests.get(
            f"{endpoint}/openai/models?api-version=2024-06-01",
            headers={"Authorization": f"Bearer {token.token}"},
            timeout=8,
        )
        if resp.status_code == 200:
            return {"name": "Voice Live API", "status": "healthy", "detail": endpoint}
        return {"name": "Voice Live API", "status": "unhealthy", "detail": f"HTTP {resp.status_code}"}
    except Exception:
        return {"name": "Voice Live API", "status": "unhealthy", "detail": "Connection failed"}


def _check_foundry_agent() -> dict:
    """Check if the Foundry agent is reachable and returns config."""
    if not settings.foundry_agent_name or not settings.foundry_project_endpoint:
        return {"name": "Foundry Agent", "status": "unknown", "detail": "Not configured"}
    project = settings.foundry_project_endpoint.rstrip("/")
    agent = settings.foundry_agent_name
    url = f"{project}/agents/{agent}?api-version=2025-05-15-preview"
    try:
        token = get_credential().get_token("https://ai.azure.com/.default")
        resp = http_requests.get(url, headers={"Authorization": f"Bearer {token.token}"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            display = data.get("versions", {}).get("latest", {}).get("definition", {}).get("model", agent)
            return {"name": "Foundry Agent", "status": "healthy", "detail": f"{agent} (model: {display})"}
        return {"name": "Foundry Agent", "status": "unhealthy", "detail": f"HTTP {resp.status_code}"}
    except Exception:
        return {"name": "Foundry Agent", "status": "unhealthy", "detail": "Connection failed"}


def _check_azure_openai() -> dict:
    """Check if the Azure OpenAI chat deployment is accessible via a zero-token completions probe."""
    endpoint = settings.azure_openai_endpoint.rstrip("/")
    deployment = settings.azure_openai_chat_deployment
    if not endpoint:
        return {"name": "Azure OpenAI", "status": "unknown", "detail": "AZURE_OPENAI_ENDPOINT not set"}
    try:
        token = get_credential().get_token("https://cognitiveservices.azure.com/.default")
        # Send a minimal completions request (max_tokens=1) to verify the deployment is live
        resp = http_requests.post(
            f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-06-01",
            headers={"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"},
            json={"messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
            timeout=10,
        )
        if resp.status_code == 200:
            return {"name": "Azure OpenAI", "status": "healthy", "detail": f"Deployment: {deployment}"}
        return {"name": "Azure OpenAI", "status": "unhealthy", "detail": f"HTTP {resp.status_code}"}
    except Exception:
        return {"name": "Azure OpenAI", "status": "unhealthy", "detail": "Connection failed"}


def _check_acs() -> dict:
    """Check if ACS connection string is set and phone number is configured."""
    if not settings.acs_connection_string:
        return {"name": "ACS (Telephony)", "status": "unhealthy", "detail": "ACS_CONNECTION_STRING not set"}
    phone = settings.acs_phone_number
    if not phone:
        return {"name": "ACS (Telephony)", "status": "degraded", "detail": "Connected, but ACS_PHONE_NUMBER not set (no outbound)"}
    return {"name": "ACS (Telephony)", "status": "healthy", "detail": f"Phone: {phone}"}


def _check_azure_auth() -> dict:
    """Check if Azure credential can acquire a token."""
    try:
        token = get_credential().get_token("https://cognitiveservices.azure.com/.default")
        # Mask the token, just confirm it's non-empty
        if token.token:
            return {"name": "Azure Auth", "status": "healthy", "detail": "Token acquired"}
        return {"name": "Azure Auth", "status": "unhealthy", "detail": "Empty token"}
    except Exception:
        return {"name": "Azure Auth", "status": "unhealthy", "detail": "Token acquisition failed"}


@router.get("/api/health/services")
async def health_services():
    """Run all health checks in parallel and return results."""
    loop = asyncio.get_event_loop()
    checks = [
        _check_backend,
        _check_azure_auth,
        _check_devtunnel,
        _check_acs,
        _check_cognitive_services,
        _check_azure_openai,
        _check_foundry_agent,
    ]
    results = await asyncio.gather(
        *[loop.run_in_executor(None, fn) for fn in checks],
        return_exceptions=True,
    )
    services = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            services.append({"name": checks[i].__name__, "status": "error", "detail": str(r)[:120]})
        else:
            services.append(r)

    overall = "healthy"
    for s in services:
        if s["status"] == "unhealthy":
            overall = "unhealthy"
            break
        if s["status"] in ("degraded", "unknown"):
            overall = "degraded"

    return JSONResponse({"overall": overall, "services": services})
