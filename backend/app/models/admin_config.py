from sqlalchemy import Column, Integer, JSON

from backend.app.db.database import Base


class AdminConfig(Base):
    __tablename__ = "admin_config"

    id = Column(Integer, primary_key=True)
    routing_rules = Column(JSON, nullable=False)
    sla_targets = Column(JSON, nullable=False)
