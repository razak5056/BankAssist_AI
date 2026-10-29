from typing import Optional
from pydantic import BaseModel, Field

from backend.app.schemas.ticket import TicketResponse


class AgentQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class AgentAnswer(BaseModel):
    answer: str
    mode: str
    source: str
    category: Optional[str] = None
    intent: Optional[str] = None
    clarification_options: list[str] = []
    ticket_created: bool = False
    ticket: Optional[TicketResponse] = None
