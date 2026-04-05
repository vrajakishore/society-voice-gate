from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.models import Complaint, ComplaintCreate, ComplaintStatusUpdate, TicketEvent

logger = logging.getLogger(__name__)

_lock = Lock()
_path = Path(__file__).resolve().parents[2] / "data" / "tickets.json"


def _ensure() -> None:
    _path.parent.mkdir(parents=True, exist_ok=True)
    if not _path.exists():
        _path.write_text("[]", encoding="utf-8")


def _load() -> list[dict[str, Any]]:
    _ensure()
    try:
        raw = _path.read_text(encoding="utf-8").strip()
        return json.loads(raw) if raw else []
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to load tickets from %s", _path)
        return []


def _save(items: list[dict[str, Any]]) -> None:
    _ensure()
    tmp = _path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=True, indent=2), encoding="utf-8")
    tmp.replace(_path)


def create_ticket(data: ComplaintCreate) -> Complaint:
    ticket = Complaint(**data.model_dump(mode="json"))
    ticket.events.append(TicketEvent(type="created").model_dump())
    with _lock:
        items = _load()
        items.append(ticket.model_dump(mode="json"))
        _save(items)
    logger.info(
        "Ticket created: %s  caller=%s  category=%s  priority=%s",
        ticket.id, ticket.caller_phone, ticket.category, ticket.priority,
    )
    return ticket


def get_ticket(ticket_id: str) -> Complaint | None:
    with _lock:
        items = _load()
    for item in items:
        if str(item.get("id", "")).upper() == ticket_id.upper():
            return Complaint(**item)
    return None


def update_ticket(ticket_id: str, update: ComplaintStatusUpdate) -> Complaint | None:
    with _lock:
        items = _load()
        for idx, item in enumerate(items):
            if str(item.get("id", "")).upper() != ticket_id.upper():
                continue
            ticket = Complaint(**item)
            if update.status is not None:
                ticket.status = update.status
                ticket.events.append(
                    TicketEvent(type=f"status_changed_to_{update.status.value}").model_dump()
                )
            if update.assigned_to is not None:
                ticket.assigned_to = update.assigned_to
                ticket.events.append(
                    TicketEvent(type="assigned", note=update.assigned_to).model_dump()
                )
            if update.resolution_notes is not None:
                ticket.resolution_notes = update.resolution_notes
            ticket.last_updated_at = datetime.now(timezone.utc).isoformat()
            items[idx] = ticket.model_dump(mode="json")
            _save(items)
            return ticket
    return None


def list_tickets(
    category: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[Complaint]:
    with _lock:
        items = _load()
    result = []
    for item in items:
        if category and item.get("category") != category:
            continue
        if status and item.get("status") != status:
            continue
        result.append(Complaint(**item))
    result.sort(key=lambda t: t.created_at, reverse=True)
    return result[:limit]
