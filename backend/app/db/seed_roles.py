from backend.app.db.database import SessionLocal
from backend.app.models import Role


def seed_roles():
    db = SessionLocal()

    roles = [
        {
            "name": "Customer",
            "description": "Bank customer who creates support tickets",
        },
        {
            "name": "L1 Support",
            "description": "First-level banking support executive",
        },
        {
            "name": "L2 Senior Support",
            "description": "Senior support specialist",
        },
        {
            "name": "L3 Support Manager",
            "description": "Support manager who handles escalations",
        },
        {
            "name": "Admin",
            "description": "System administrator",
        },
    ]

    try:
        for role_data in roles:
            existing_role = (
                db.query(Role)
                .filter(Role.name == role_data["name"])
                .first()
            )

            if not existing_role:
                role = Role(**role_data)
                db.add(role)

        db.commit()
        print("Default roles created successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error creating roles: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()