from pathlib import Path
import backend.app.core.config  # Automatically loads .env file

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.admin import router as admin_router
from backend.app.api.assistant import router as assistant_router
from backend.app.api.auth import router as auth_router
from backend.app.api.tickets import router as tickets_router
from backend.app.core.auth import get_current_user, require_role, require_roles
from backend.app.db.database import get_db
from backend.app.models.role import Role
from backend.app.models.ticket import Ticket
from backend.app.models.user import User
from sqlalchemy.orm import Session

app = FastAPI(
    title="BankAssist AI",
    description="Intelligent Banking Dispute Resolution and Automatic Ticket Routing Platform",
    version="1.0.0",
)


# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "BankAssist AI",
    }


# API Routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(assistant_router)
app.include_router(tickets_router)


@app.get("/auth/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.name
    }


@app.get("/customer/dashboard")
def customer_dashboard(
    current_user: User = Depends(require_role("Customer")),
    db: Session = Depends(get_db),
):
    open_tickets = (
        db.query(Ticket)
        .filter(Ticket.customer_id == current_user.id, Ticket.status.notin_(["Resolved", "Closed"]))
        .count()
    )
    total_tickets = (
        db.query(Ticket)
        .filter(Ticket.customer_id == current_user.id)
        .count()
    )

    return {
        "message": f"Welcome back, {current_user.username}",
        "customer": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "account_status": "active" if current_user.is_active else "inactive",
        },
        "summary": {
            "open_tickets": open_tickets,
            "total_tickets": total_tickets,
            "ticket_status": f"{open_tickets} active dispute(s) being tracked." if open_tickets > 0 else "No active disputes.",
        },
        "available_actions": [
            {
                "label": "Ask AI Banking Agent",
                "method": "POST",
                "endpoint": "/assistant/ask",
            },
            {
                "label": "View My Disputes",
                "method": "GET",
                "endpoint": "/tickets/my",
            },
        ],
    }


@app.get("/support/dashboard")
def support_dashboard(
    current_user: User = Depends(
        require_roles("L1 Support", "L2 Senior Support", "L3 Support Manager")
    ),
    db: Session = Depends(get_db),
):
    user_tier = current_user.role.name
    tier_tickets = db.query(Ticket).filter(Ticket.assigned_tier == user_tier)
    assigned_to_me = tier_tickets.filter(Ticket.assigned_to_id == current_user.id, Ticket.status.notin_(["Resolved", "Closed"])).count()
    awaiting_response = tier_tickets.filter(Ticket.status.in_(["Open", "Assigned"])).count()
    escalations_count = db.query(Ticket).filter(Ticket.status.like("Escalated%")).count()

    return {
        "message": "Welcome to Support Dashboard",
        "support_user": current_user.username,
        "role": current_user.role.name,
        "metrics": {
            "assigned_to_me": assigned_to_me,
            "awaiting_response": awaiting_response,
            "escalations": escalations_count,
        },
    }


@app.get("/support/l1/dashboard")
def l1_support_dashboard(
    current_user: User = Depends(require_role("L1 Support")),
    db: Session = Depends(get_db),
):
    assigned_to_me = db.query(Ticket).filter(Ticket.assigned_to_id == current_user.id, Ticket.status.notin_(["Resolved", "Closed"])).count()
    awaiting_response = db.query(Ticket).filter(Ticket.assigned_to_id == current_user.id, Ticket.status.in_(["Open", "Assigned", "In Progress"])).count()
    return {
        "message": f"Welcome to L1 Support Dashboard - {current_user.username}",
        "support_user": current_user.username,
        "role": current_user.role.name,
        "metrics": {
            "assigned_to_me": assigned_to_me,
            "awaiting_response": awaiting_response,
            "escalations": 0,
        },
    }


@app.get("/support/l2/dashboard")
def l2_support_dashboard(
    current_user: User = Depends(require_role("L2 Senior Support")),
    db: Session = Depends(get_db),
):
    assigned_to_me = db.query(Ticket).filter(Ticket.assigned_to_id == current_user.id, Ticket.status.notin_(["Resolved", "Closed"])).count()
    awaiting_response = db.query(Ticket).filter(Ticket.assigned_to_id == current_user.id, Ticket.status.in_(["Open", "Assigned", "In Progress", "Escalated to L2"])).count()
    return {
        "message": f"Welcome to L2 Senior Support Dashboard - {current_user.username}",
        "support_user": current_user.username,
        "role": current_user.role.name,
        "metrics": {
            "assigned_to_me": assigned_to_me,
            "awaiting_response": awaiting_response,
            "escalations": assigned_to_me,
        },
    }


@app.get("/support/l3/dashboard")
def l3_support_dashboard(
    current_user: User = Depends(require_role("L3 Support Manager")),
    db: Session = Depends(get_db),
):
    assigned_to_me = db.query(Ticket).filter(Ticket.assigned_to_id == current_user.id, Ticket.status.notin_(["Resolved", "Closed"])).count()
    awaiting_response = db.query(Ticket).filter(Ticket.assigned_to_id == current_user.id, Ticket.status.in_(["Open", "Assigned", "In Progress", "Escalated to L3"])).count()
    total_escalations = db.query(Ticket).filter(Ticket.status.like("Escalated%")).count()
    return {
        "message": f"Welcome to L3 Support Manager Dashboard - {current_user.username}",
        "support_user": current_user.username,
        "role": current_user.role.name,
        "metrics": {
            "assigned_to_me": assigned_to_me,
            "awaiting_response": awaiting_response,
            "escalations": total_escalations,
        },
    }


@app.get("/support/team")
def get_support_team(
    current_user: User = Depends(
        require_roles("L1 Support", "L2 Senior Support", "L3 Support Manager", "Admin")
    ),
    db: Session = Depends(get_db),
):
    """Returns the 4 L1 Support Executives, 2 L2 Senior Support/Specialists, and L3 Manager as per HLD."""
    l1_role = db.query(Role).filter(Role.name == "L1 Support").first()
    l2_role = db.query(Role).filter(Role.name == "L2 Senior Support").first()
    l3_role = db.query(Role).filter(Role.name == "L3 Support Manager").first()

    # L1 Executives (4)
    l1_users = (
        db.query(User)
        .filter(User.role_id == l1_role.id, User.is_active == True)
        .order_by(User.id)
        .all()
        if l1_role
        else []
    )
    l1_category_map = {
        "rajesh.l1@example.com": "UPI & Digital Payments",
        "suresh.atm@example.com": "ATM & Cash Withdrawal",
        "kavita.acc@example.com": "Account & Balance",
        "deepak.kyc@example.com": "Account Access & KYC",
    }
    l1_team = []
    for u in l1_users:
        active_tickets = (
            db.query(Ticket)
            .filter(Ticket.assigned_to_id == u.id, Ticket.status.notin_(["Resolved", "Closed"]))
            .count()
        )
        l1_team.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "category": l1_category_map.get(u.email, "Banking Dispute Specialist"),
            "active_tickets": active_tickets,
            "is_current": u.id == current_user.id,
        })

    # L2 Senior Support / Specialists (2) as per HLD
    l2_users = (
        db.query(User)
        .filter(User.role_id == l2_role.id, User.is_active == True)
        .order_by(User.id)
        .all()
        if l2_role
        else []
    )
    l2_specialization_map = {
        "anita.l2@example.com": "Complex and Unresolved Issues",
        "rohit.l2@example.com": "Cross-Category Support",
    }
    l2_role_title_map = {
        "anita.l2@example.com": "Senior Support",
        "rohit.l2@example.com": "Specialist",
    }
    l2_team = []
    for u in l2_users:
        active_tickets = (
            db.query(Ticket)
            .filter(Ticket.assigned_to_id == u.id, Ticket.status.notin_(["Resolved", "Closed"]))
            .count()
        )
        l2_team.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role_title": l2_role_title_map.get(u.email, "Senior Support"),
            "focus": l2_specialization_map.get(u.email, "Complex Disputes"),
            "active_tickets": active_tickets,
            "is_current": u.id == current_user.id,
        })

    # L3 Support Manager (1) as per HLD
    l3_user = (
        db.query(User)
        .filter(User.role_id == l3_role.id, User.is_active == True)
        .first()
        if l3_role
        else None
    )
    l3_data = None
    if l3_user:
        active_tickets = (
            db.query(Ticket)
            .filter(Ticket.assigned_to_id == l3_user.id, Ticket.status.notin_(["Resolved", "Closed"]))
            .count()
        )
        l3_data = {
            "id": l3_user.id,
            "username": l3_user.username,
            "email": l3_user.email,
            "role_title": "Support Manager",
            "focus": "High Priority / Serious Cases & SLA Overdue",
            "active_tickets": active_tickets,
            "is_current": l3_user.id == current_user.id,
        }

    return {
        "l1_count": len(l1_team),
        "l1_executives": l1_team,
        "l2_count": len(l2_team),
        "l2_specialists": l2_team,
        "l3_manager": l3_data,
    }




# Admin-only API
@app.get("/admin/dashboard")
def admin_dashboard(
    current_user: User = Depends(require_role("Admin"))
):
    return {
        "message": "Welcome to Admin Dashboard",
        "admin": current_user.username,
        "role": current_user.role.name
    }


frontend_directory = Path(__file__).resolve().parents[2] / "frontend"
uploads_directory = Path(__file__).resolve().parents[2] / "uploads"
uploads_directory.mkdir(parents=True, exist_ok=True)


# Three Separate Dashboards as per HLD
@app.get("/customer", include_in_schema=False)
@app.get("/customer/portal", include_in_schema=False)
def customer_portal():
    """Customer Dashboard: Ask questions/raise complaints, upload evidence, track ticket status."""
    return FileResponse(frontend_directory / "customer.html")


@app.get("/support", include_in_schema=False)
@app.get("/support/portal", include_in_schema=False)
def support_portal():
    """Banking Support Executive Dashboard: View assigned tickets, investigate and respond, update status."""
    return FileResponse(frontend_directory / "support.html")


@app.get("/admin", include_in_schema=False)
@app.get("/admin/portal", include_in_schema=False)
def admin_portal():
    """Admin Dashboard: Manage users & roles, configure routing & SLA, monitor escalations & reports."""
    return FileResponse(frontend_directory / "admin.html")


@app.get("/", include_in_schema=False)
def portal_gateway():
    """Main Portal Gateway: Overview and direct access to all 3 dashboards."""
    return FileResponse(frontend_directory / "index.html")


app.mount("/uploads", StaticFiles(directory=uploads_directory), name="uploads")
app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
