
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(100), unique=True, nullable=False)

    email = Column(String(255), unique=True, nullable=False)

    hashed_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True)

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    role = relationship("Role", back_populates="users")
    created_tickets = relationship("Ticket", foreign_keys="Ticket.customer_id", back_populates="customer")
    assigned_tickets = relationship("Ticket", foreign_keys="Ticket.assigned_to_id", back_populates="assigned_to")

