import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.app.db.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(50), unique=True, index=True, nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # UPI, ATM, Cards, Account, KYC
    case_type = Column(String(50), default="Complaint", nullable=False)  # Complaint, Service Request, Inquiry, Feedback
    priority = Column(String(20), default="Normal", nullable=False)  # Low, Normal, High, Urgent
    status = Column(String(50), default="Assigned", nullable=False)  # Open, Assigned, In Progress, Escalated to L2, Escalated to L3, Resolved, Closed

    assigned_tier = Column(String(50), default="L1 Support", nullable=False)
    sla_hours = Column(Integer, default=24, nullable=False)
    sla_deadline = Column(DateTime(timezone=True), nullable=True)

    ai_summary = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    evidence_filename = Column(String(255), nullable=True)
    evidence_url = Column(String(500), nullable=True)

    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    customer = relationship("User", foreign_keys=[customer_id], back_populates="created_tickets")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_tickets")
    history = relationship("TicketHistory", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketHistory.created_at.desc()")


class TicketHistory(Base):
    __tablename__ = "ticket_history"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    action = Column(String(50), nullable=False)  # CREATED, ROUTED, ESCALATED, STATUS_CHANGED, NOTE_ADDED, RESOLVED, CLOSED
    details = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket = relationship("Ticket", back_populates="history")
    actor = relationship("User", foreign_keys=[actor_id])

