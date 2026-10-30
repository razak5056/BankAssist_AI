"""
Routing & Escalation Engine for BankAssist AI.
Handles automatic assignment of tickets to support executives based on category,
priority, and SLA configurations, and manages escalation from L1 to L2 to L3.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.admin_config import AdminConfig
from backend.app.models.role import Role
from backend.app.models.ticket import Ticket, TicketHistory
from backend.app.models.user import User


DEFAULT_ROUTING_RULES = [
    {"category": "UPI", "support_tier": "L1 Support", "priority": "Normal"},
    {"category": "ATM", "support_tier": "L1 Support", "priority": "High"},
    {"category": "Cards", "support_tier": "L1 Support", "priority": "High"},
    {"category": "Account", "support_tier": "L1 Support", "priority": "Normal"},
    {"category": "KYC", "support_tier": "L1 Support", "priority": "Low"},
]

DEFAULT_SLA_TARGETS = {
    "L1 Support": 24,
    "L2 Senior Support": 48,
    "L3 Support Manager": 72,
}


def get_routing_config(db: Session) -> tuple[list[dict], dict[str, int]]:
    """Fetches the active routing rules and SLA targets from AdminConfig."""
    config = db.query(AdminConfig).filter(AdminConfig.id == 1).first()
    if config:
        return config.routing_rules, config.sla_targets
    return DEFAULT_ROUTING_RULES, DEFAULT_SLA_TARGETS


def find_assignee_for_tier(db: Session, tier_name: str, category: Optional[str] = None) -> Optional[User]:
    """
    Finds the best active support executive for a tier based on HLD:
    - For L1 Support: Assigns to the specialized L1 executive matching the category:
        1. UPI & Digital Payments -> Rajesh Kumar (L1 - UPI)
        2. ATM & Cash Withdrawal  -> Suresh Patel (L1 - ATM)
        3. Account & Balance      -> Kavita Rao (L1 - Account)
        4. Account Access & KYC   -> Deepak Verma (L1 - KYC)
    - If no exact specialist matches or for senior tiers (L2/L3), assigns to least loaded executive.
    """
    role = db.query(Role).filter(Role.name == tier_name).first()
    if not role:
        return None

    # Get active users with this role
    users = db.query(User).filter(User.role_id == role.id, User.is_active == True).all()
    if not users:
        return None

    if len(users) == 1:
        return users[0]

    # Category-specific routing for L1 Banking Support Executives (HLD Support Team Mapping)
    if tier_name == "L1 Support" and category:
        cat_lower = category.lower()
        if "kyc" in cat_lower or "access" in cat_lower or "verification" in cat_lower:
            target_keyword = "kyc"
        elif "upi" in cat_lower or "digital" in cat_lower:
            target_keyword = "upi"
        elif "atm" in cat_lower or "cash" in cat_lower:
            target_keyword = "atm"
        elif "account" in cat_lower or "card" in cat_lower or "balance" in cat_lower:
            target_keyword = "account"
        else:
            target_keyword = None

        if target_keyword:
            for u in users:
                user_ident = (u.username + " " + u.email).lower()
                if target_keyword in user_ident:
                    return u

    # Specialization routing for L2 Senior Support / Specialists (HLD: 2 persons)
    # - Anita Sharma: Senior Support (Complex & Unresolved Issues)
    # - Rohit Mehra: Specialist (Cross-Category Support)
    if tier_name == "L2 Senior Support" and category:
        cat_lower = category.lower()
        if "cross" in cat_lower or "specialist" in cat_lower or "multi" in cat_lower or "card" in cat_lower:
            target_l2 = "rohit"
        elif "complex" in cat_lower or "unresolved" in cat_lower or "senior" in cat_lower or "debit" in cat_lower or "upi" in cat_lower or "atm" in cat_lower:
            target_l2 = "anita"
        else:
            target_l2 = None

        if target_l2:
            for u in users:
                if target_l2 in (u.username + " " + u.email).lower():
                    return u

    # Select the executive with the lowest number of active assigned tickets (Least-loaded)
    user_ids = [u.id for u in users]
    ticket_counts = (
        db.query(Ticket.assigned_to_id, func.count(Ticket.id))
        .filter(Ticket.assigned_to_id.in_(user_ids), Ticket.status.notin_(["Resolved", "Closed"]))
        .group_by(Ticket.assigned_to_id)
        .all()
    )
    counts_map = {uid: 0 for uid in user_ids}
    for uid, count in ticket_counts:
        counts_map[uid] = count

    least_loaded_id = min(counts_map, key=counts_map.get)
    return db.query(User).filter(User.id == least_loaded_id).first()


def generate_ticket_number() -> str:
    """Generates a human-readable unique banking dispute ticket number."""
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_id = uuid.uuid4().hex[:5].upper()
    return f"TK-{now_str}-{short_id}"


def create_and_route_ticket(
    db: Session,
    customer: User,
    title: str,
    description: str,
    category: str,
    priority: str = "Normal",
    ai_summary: Optional[str] = None,
    case_type: str = "Complaint",
) -> Ticket:
    """
    Creates a new support ticket and automatically routes it to an L1 executive
    based on AdminConfig rules and SLA targets.
    """
    routing_rules, sla_targets = get_routing_config(db)

    # Determine assigned tier and default priority from routing rules
    assigned_tier = "L1 Support"
    final_priority = priority

    for rule in routing_rules:
        if rule.get("category", "").lower() == category.lower():
            assigned_tier = rule.get("support_tier", "L1 Support")
            # If the priority wasn't elevated by urgent keywords, adopt admin config priority
            if priority in ("Normal", "Low") and rule.get("priority"):
                final_priority = rule.get("priority")
            break

    # Calculate SLA deadline
    sla_hours = sla_targets.get(assigned_tier, 24)
    sla_deadline = datetime.now(timezone.utc) + timedelta(hours=sla_hours)

    # Find executive to assign (auto-routes to specialized L1 executive)
    assignee = find_assignee_for_tier(db, assigned_tier, category=category)

    ticket = Ticket(
        ticket_number=generate_ticket_number(),
        title=title,
        description=description,
        category=category,
        case_type=case_type,
        priority=final_priority,
        status="Assigned" if assignee else "Open",
        assigned_tier=assigned_tier,
        sla_hours=sla_hours,
        sla_deadline=sla_deadline,
        ai_summary=ai_summary,
        customer_id=customer.id,
        assigned_to_id=assignee.id if assignee else None,
    )
    db.add(ticket)
    db.flush()

    # Log creation and routing in TicketHistory
    assigned_name = assignee.username if assignee else "Unassigned Queue"
    deadline_formatted = sla_deadline.strftime("%d %b %Y, %I:%M %p UTC")
    history_entry = TicketHistory(
        ticket_id=ticket.id,
        actor_id=customer.id,
        action="CREATED_AND_ROUTED",
        details=f"Ticket created automatically by AI Agent for category '{category}' and routed to {assigned_tier} ({assigned_name}). Priority: {final_priority}. SLA Window: {sla_hours}h. Target Resolution Deadline: {deadline_formatted}.",
    )
    db.add(history_entry)
    db.commit()
    db.refresh(ticket)

    return ticket


def escalate_ticket(
    db: Session,
    ticket: Ticket,
    actor: User,
    reason: str,
) -> Ticket:
    """
    Escalates a ticket to the next tier:
    L1 Support -> L2 Senior Support -> L3 Support Manager
    """
    _, sla_targets = get_routing_config(db)

    next_tier_map = {
        "L1 Support": "L2 Senior Support",
        "L2 Senior Support": "L3 Support Manager",
    }

    current_tier = ticket.assigned_tier
    next_tier = next_tier_map.get(current_tier)

    if not next_tier:
        raise ValueError(f"Ticket is already at the highest escalation level ({current_tier}).")

    new_assignee = find_assignee_for_tier(db, next_tier, category=f"{reason} {ticket.category}")
    new_sla_hours = sla_targets.get(next_tier, 48)
    new_sla_deadline = datetime.now(timezone.utc) + timedelta(hours=new_sla_hours)

    ticket.assigned_tier = next_tier
    ticket.assigned_to_id = new_assignee.id if new_assignee else None
    ticket.status = f"Escalated to {next_tier.split()[0]}"
    ticket.sla_hours = new_sla_hours
    ticket.sla_deadline = new_sla_deadline

    assigned_str = new_assignee.username if new_assignee else "Unassigned Queue"
    deadline_formatted = new_sla_deadline.strftime("%d %b %Y, %I:%M %p UTC")
    history_entry = TicketHistory(
        ticket_id=ticket.id,
        actor_id=actor.id,
        action="ESCALATED",
        details=f"Ticket escalated from {current_tier} to {next_tier} ({assigned_str}) by {actor.username}. Reason: {reason}. Escalation SLA: {new_sla_hours}h. New Resolution Deadline: {deadline_formatted}.",
    )
    db.add(history_entry)
    db.commit()
    db.refresh(ticket)

    return ticket

