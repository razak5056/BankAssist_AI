
from backend.app.db.database import Base, engine
from backend.app.models import User, Role, AdminConfig, Ticket, TicketHistory


def create_tables():
    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully!")


if __name__ == "__main__":
    create_tables()
