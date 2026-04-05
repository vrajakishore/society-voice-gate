from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Channel(str, Enum):
    voice = "voice"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    emergency = "emergency"


class TicketStatus(str, Enum):
    open = "open"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class TicketCategory(str, Enum):
    gate_security = "gate_security"
    lift = "lift"
    plumbing = "plumbing"
    electrical = "electrical"
    parking = "parking"
    housekeeping = "housekeeping"
    noise = "noise"
    maintenance = "maintenance"
    emergency = "emergency"
    general = "general"


class TicketEvent(BaseModel):
    type: str
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    note: str = ""


class Complaint(BaseModel):
    id: str = Field(default_factory=lambda: f"C-{uuid.uuid4().hex[:6].upper()}")
    channel: Channel = Channel.voice
    category: TicketCategory = TicketCategory.general
    sub_category: str = ""
    priority: Priority = Priority.medium
    location: str = ""
    caller_phone: str = ""
    description: str = ""
    status: TicketStatus = TicketStatus.open
    assigned_to: str = ""
    transcript: str = ""
    resolution_notes: str = ""
    source_call_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    events: list[dict[str, Any]] = Field(default_factory=list)


class ComplaintCreate(BaseModel):
    channel: Channel = Channel.voice
    category: TicketCategory = TicketCategory.general
    sub_category: str = ""
    priority: Priority = Priority.medium
    location: str = ""
    caller_phone: str = ""
    description: str = ""
    transcript: str = ""
    source_call_id: str = ""


class ComplaintStatusUpdate(BaseModel):
    status: TicketStatus | None = None
    assigned_to: str | None = None
    resolution_notes: str | None = None
