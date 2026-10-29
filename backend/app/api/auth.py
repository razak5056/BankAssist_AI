from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.models import User

from fastapi.security import OAuth2PasswordRequestForm

from backend.app.core.security import verify_password, create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Find user by email or username (case-insensitive & trimmed)
    login_id = form_data.username.strip().lower()
    user = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.email) == login_id,
                func.lower(User.username) == login_id,
            )
        )
        .first()
    )

    # Verify user and password
    if not user or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # Check whether user is active
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive",
        )

    # Create JWT token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.name,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.name,
        },
    }
