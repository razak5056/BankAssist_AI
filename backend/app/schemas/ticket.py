from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


CategoryType = Literal["UPI", "ATM", "Cards", "Account", "KYC"]
PriorityType = Literal["Low", "Normal", "High", "Urgent"]
TicketStatus = Literal[
    "Open",
    "Assigned",
    "In Progress",
    "Escalated",
    "Escalated to L2",
    "Escalated to L3",
    "Resolved",
    "Closed",
]


class TicketHistoryResponse(BaseModel):
    id: int
    action: str
    details: str
    actor_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    assigned_tier: str
    sla_hours: int
    sla_deadline: Optional[datetime] = None
    ai_summary: Optional[str] = None
    resolution_notes: Optional[str] = None
    evidence_filename: Optional[str] = None
    evidence_url: Optional[str] = None
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    history: list[TicketHistoryResponse] = []

    class Config:
        from_attributes = True


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    resolution_notes: Optional[str] = Field(None, max_length=1000)
    escalate: bool = False
    escalation_reason: Optional[str] = Field(None, max_length=500)

