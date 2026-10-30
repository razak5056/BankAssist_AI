from typing import Any, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.ticket import TicketResponse


class AgentQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    history: Optional[list[dict[str, Any]]] = []


class AgentAnswer(BaseModel):
    answer: str
    mode: str
    source: str
    category: Optional[str] = None
    intent: Optional[str] = None
    case_type: Optional[str] = "Inquiry"
    clarification_options: list[str] = []
    ticket_created: bool = False
    ticket: Optional[TicketResponse] = None
