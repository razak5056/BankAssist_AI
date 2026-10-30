from pathlib import Path
import shutil
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from backend.app.agents.banking_agent import format_ticket_dict
from backend.app.core.auth import get_current_user, require_role, require_roles
from backend.app.db.database import get_db
from backend.app.models.ticket import Ticket, TicketHistory
from backend.app.models.user import User
from backend.app.schemas.ticket import CustomerTicketReply, TicketResponse, TicketStatusUpdate
from backend.app.services.routing_engine import escalate_ticket

router = APIRouter(prefix="/tickets", tags=["Ticket Management"])

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads" / "evidence"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ------------------ CUSTOMER ENDPOINTS ------------------

@router.get("/my", response_model=list[TicketResponse])
def get_my_tickets(
    current_user: User = Depends(require_role("Customer")),
    db: Session = Depends(get_db),
):
    """Returns all support tickets created by the logged-in customer."""
    tickets = (
        db.query(Ticket)
        .filter(Ticket.customer_id == current_user.id)
        .order_by(desc(Ticket.created_at))
        .all()
    )
    return [format_ticket_dict(t) for t in tickets]


@router.get("/my/{ticket_id}", response_model=TicketResponse)
def get_my_ticket_detail(
    ticket_id: int,
    current_user: User = Depends(require_role("Customer")),
    db: Session = Depends(get_db),
):
    """Returns details and history of a specific ticket belonging to the customer."""
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.customer_id == current_user.id)
        .first()
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return format_ticket_dict(ticket)


@router.post("/my/{ticket_id}/evidence", response_model=TicketResponse)
async def upload_ticket_evidence(
    ticket_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("Customer")),
    db: Session = Depends(get_db),
):
    """
    Allows customer to upload unverified document/evidence
    (e.g., screenshot, transaction receipt, account statement) for a dispute ticket.
    Stored unverified per HLD specifications.
    """
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.customer_id == current_user.id)
        .first()
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Sanitize and persist file
    clean_orig_name = Path(file.filename or "evidence.dat").name
    safe_filename = f"{ticket.ticket_number}_{uuid.uuid4().hex[:8]}_{clean_orig_name}"
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ticket.evidence_filename = clean_orig_name
    ticket.evidence_url = f"/uploads/evidence/{safe_filename}"

    # Log in audit trail
    history = TicketHistory(
        ticket_id=ticket.id,
        actor_id=current_user.id,
        action="EVIDENCE_UPLOADED",
        details=f"Customer uploaded dispute evidence file: '{clean_orig_name}' (Stored unverified as per banking dispute policy).",
    )
    db.add(history)
    db.commit()
    db.refresh(ticket)

    return format_ticket_dict(ticket)


@router.post("/my/{ticket_id}/reply", response_model=TicketResponse)
def customer_reply_to_ticket(
    ticket_id: int,
    payload: CustomerTicketReply,
    current_user: User = Depends(require_role("Customer")),
    db: Session = Depends(get_db),
):
    """Allows customer to provide additional details or reply to support inquiry."""
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.customer_id == current_user.id)
        .first()
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    clean_message = payload.message.strip()

    # If ticket was waiting for customer response, change status back to In Progress
    if ticket.status == "Awaiting Customer Response":
        ticket.status = "In Progress"

    # Add audit entry
    history = TicketHistory(
        ticket_id=ticket.id,
        actor_id=current_user.id,
        action="CUSTOMER_RESPONSE",
        details=f"Customer provided additional details: \"{clean_message}\"",
    )
    db.add(history)
    db.commit()
    db.refresh(ticket)

    return format_ticket_dict(ticket)


# ------------------ SUPPORT WORKSPACE ENDPOINTS ------------------

@router.get("/support/queue", response_model=list[TicketResponse])
def get_support_tickets_queue(
    desk_only: bool = True,
    current_user: User = Depends(
        require_roles("L1 Support", "L2 Senior Support", "L3 Support Manager")
    ),
    db: Session = Depends(get_db),
):
    """
    Returns tickets for the support executive:
    - If desk_only is True (default): Returns ONLY tickets assigned to the active executive (current_user.id).
    - If desk_only is False: Returns all tickets in the executive's tier queue.
    """
    user_tier = current_user.role.name
    query = db.query(Ticket)

    if desk_only:
        query = query.filter(Ticket.assigned_to_id == current_user.id)
    else:
        if user_tier == "L1 Support":
            query = query.filter(Ticket.assigned_tier == "L1 Support")
        elif user_tier == "L2 Senior Support":
            query = query.filter(Ticket.assigned_tier == "L2 Senior Support")
        elif user_tier == "L3 Support Manager":
            query = query.filter(Ticket.assigned_tier == "L3 Support Manager")

    tickets = query.order_by(desc(Ticket.created_at)).all()
    return [format_ticket_dict(t) for t in tickets]


@router.get("/support/escalated", response_model=list[TicketResponse])
def get_escalated_tickets(
    desk_only: bool = True,
    current_user: User = Depends(
        require_roles("L1 Support", "L2 Senior Support", "L3 Support Manager", "Admin")
    ),
    db: Session = Depends(get_db),
):
    """
    Returns escalated dispute tickets for the executive workspace:
    - L1 Support: Disputes escalated by this executive, assigned to this executive,
      or belonging to their category desk (or all if desk_only=False).
    - L2 Senior Support: Disputes escalated to L2 / assigned to this senior specialist.
    - L3 Support Manager / Admin: All escalated disputes across the organization.
    """
    user_tier = current_user.role.name
    query = db.query(Ticket).filter(Ticket.status.like("Escalated%"))

    if user_tier == "L1 Support":
        if desk_only:
            escalated_by_subquery = (
                db.query(TicketHistory.ticket_id)
                .filter(TicketHistory.action == "ESCALATED", TicketHistory.actor_id == current_user.id)
            )
            email_or_name = (current_user.email + " " + current_user.username).lower()
            cat_keywords = []
            if "kavita" in email_or_name or "acc" in email_or_name:
                cat_keywords = ["account", "card", "balance"]
            elif "rajesh" in email_or_name or "upi" in email_or_name:
                cat_keywords = ["upi", "digital"]
            elif "suresh" in email_or_name or "atm" in email_or_name:
                cat_keywords = ["atm", "cash"]
            elif "deepak" in email_or_name or "kyc" in email_or_name:
                cat_keywords = ["kyc", "access", "verification"]

            conditions = [
                Ticket.id.in_(escalated_by_subquery),
                Ticket.assigned_to_id == current_user.id,
            ]
            for kw in cat_keywords:
                conditions.append(Ticket.category.ilike(f"%{kw}%"))

            query = query.filter(or_(*conditions))
    elif user_tier == "L2 Senior Support":
        if desk_only:
            query = query.filter(
                or_(
                    Ticket.assigned_to_id == current_user.id,
                    Ticket.assigned_tier == "L2 Senior Support",
                )
            )
        else:
            query = query.filter(Ticket.assigned_tier.in_(["L2 Senior Support", "L3 Support Manager"]))
    # L3 Support Manager and Admin see all escalated tickets

    tickets = query.order_by(desc(Ticket.updated_at)).all()
    return [format_ticket_dict(t) for t in tickets]


@router.patch("/support/{ticket_id}/update", response_model=TicketResponse)
def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    current_user: User = Depends(
        require_roles("L1 Support", "L2 Senior Support", "L3 Support Manager")
    ),
    db: Session = Depends(get_db),
):
    """Updates ticket status, adds resolution notes, or escalates to senior tier."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # If escalation requested
    if payload.escalate:
        reason = payload.escalation_reason or "Escalated by support executive for senior review."
        try:
            ticket = escalate_ticket(db, ticket, current_user, reason)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return format_ticket_dict(ticket)

    # Status / Resolution update
    old_status = ticket.status
    ticket.status = payload.status
    if payload.resolution_notes:
        ticket.resolution_notes = payload.resolution_notes

    # Add history entry
    note_details = f"Status updated from '{old_status}' to '{payload.status}' by {current_user.username} ({current_user.role.name})."
    if payload.resolution_notes:
        note_details += f" Notes: {payload.resolution_notes}"

    history = TicketHistory(
        ticket_id=ticket.id,
        actor_id=current_user.id,
        action="STATUS_UPDATED",
        details=note_details,
    )
    db.add(history)
    db.commit()
    db.refresh(ticket)

    return format_ticket_dict(ticket)


# ------------------ ADMIN ENDPOINTS ------------------

@router.get("/admin/all", response_model=list[TicketResponse])
def get_all_tickets_admin(
    _: User = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Admin endpoint to view all system tickets."""
    tickets = db.query(Ticket).order_by(desc(Ticket.created_at)).all()
    return [format_ticket_dict(t) for t in tickets]

