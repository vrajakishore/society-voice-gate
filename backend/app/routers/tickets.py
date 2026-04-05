"""
tickets.py — REST API for complaint ticket management.

Endpoints:
  GET    /api/tickets              — list tickets (filter by category, status)
  GET    /api/tickets/{id}         — get single ticket
  PATCH  /api/tickets/{id}         — update status / assigned_to / resolution_notes
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.models import Complaint, ComplaintStatusUpdate
from app.services import ticket_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/tickets", response_model=list[Complaint])
def list_tickets(
    category: Annotated[str | None, Query(description="Filter by category")] = None,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    return ticket_service.list_tickets(category=category, status=status, limit=limit)


@router.get("/tickets/{ticket_id}", response_model=Complaint)
def get_ticket(ticket_id: str):
    ticket = ticket_service.get_ticket(ticket_id.upper())
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=Complaint)
def update_ticket(ticket_id: str, update: ComplaintStatusUpdate):
    ticket = ticket_service.update_ticket(ticket_id.upper(), update)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
