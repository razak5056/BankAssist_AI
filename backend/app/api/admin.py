from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.auth import require_role
from backend.app.core.security import hash_password
from backend.app.db.database import get_db
from backend.app.models import Role, User, Ticket
from backend.app.models.admin_config import AdminConfig
from backend.app.schemas.admin import AdminConfigUpdate, AdminOverview
from backend.app.schemas.user import AdminUserCreate, AdminUserResponse
from sqlalchemy import func

router = APIRouter(prefix="/admin", tags=["Administration"])

DEFAULT_ROUTING_RULES = [
    {"category": "UPI", "support_tier": "L1 Support", "priority": "Normal"},
    {"category": "ATM", "support_tier": "L1 Support", "priority": "Normal"},
    {"category": "Cards", "support_tier": "L1 Support", "priority": "High"},
    {"category": "Account", "support_tier": "L1 Support", "priority": "Normal"},
    {"category": "KYC", "support_tier": "L1 Support", "priority": "Low"},
]
DEFAULT_SLA_TARGETS = {
    "L1 Support": 24,
    "L2 Senior Support": 48,
    "L3 Support Manager": 72,
}


def get_or_create_admin_config(db: Session) -> AdminConfig:
    AdminConfig.__table__.create(bind=db.get_bind(), checkfirst=True)
    config = db.query(AdminConfig).filter(AdminConfig.id == 1).first()
    if config is None:
        config = AdminConfig(
            id=1,
            routing_rules=DEFAULT_ROUTING_RULES,
            sla_targets=DEFAULT_SLA_TARGETS,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("/overview", response_model=AdminOverview)
def admin_overview(
    _: User = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    role_counts = {
        role_name: 0
        for role_name in (
            "Customer",
            "L1 Support",
            "L2 Senior Support",
            "L3 Support Manager",
            "Admin",
        )
    }
    for role_name, count in (
        db.query(Role.name, func.count(User.id))
        .outerjoin(User, User.role_id == Role.id)
        .group_by(Role.name)
        .all()
    ):
        role_counts[role_name] = count

    total_tickets = db.query(Ticket).count()
    open_tickets = db.query(Ticket).filter(Ticket.status.notin_(["Resolved", "Closed"])).count()
    escalated_tickets = db.query(Ticket).filter(Ticket.status.like("Escalated%")).count()
    resolved_tickets = db.query(Ticket).filter(Ticket.status.in_(["Resolved", "Closed"])).count()

    return {
        "account_count": sum(role_counts.values()),
        "role_counts": role_counts,
        "ticket_metrics": {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "escalated_tickets": escalated_tickets,
            "resolved_tickets": resolved_tickets,
        },
        "message": f"Active system monitoring: {open_tickets} open tickets, {escalated_tickets} escalated cases across {sum(role_counts.values())} accounts.",
    }


@router.get("/config")
def read_admin_config(
    _: User = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    config = get_or_create_admin_config(db)
    return {"routing_rules": config.routing_rules, "sla_targets": config.sla_targets}


@router.put("/config")
def update_admin_config(
    settings: AdminConfigUpdate,
    _: User = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    config = get_or_create_admin_config(db)
    config.routing_rules = [rule.model_dump() for rule in settings.routing_rules]
    config.sla_targets = settings.sla_targets
    db.commit()
    db.refresh(config)
    return {"routing_rules": config.routing_rules, "sla_targets": config.sla_targets}


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    _: User = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.id.desc()).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.name,
            "is_active": user.is_active,
        }
        for user in users
    ]


@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    user_data: AdminUserCreate,
    _: User = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    email = str(user_data.email)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    role = db.query(Role).filter(Role.name == user_data.role).first()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Selected role is not configured",
        )

    user = User(
        username=user_data.username,
        email=email,
        hashed_password=hash_password(user_data.password),
        role_id=role.id,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create account",
        ) from exc

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": role.name,
        "is_active": user.is_active,
    }
