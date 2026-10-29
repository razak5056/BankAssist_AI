
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token
from backend.app.db.database import get_db
from backend.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = decode_access_token(token)
        raw_user_id = payload.get("sub")

        if not isinstance(raw_user_id, str) or not raw_user_id.isdecimal():
            raise ValueError("Invalid token subject")

        user_id = int(raw_user_id)

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    return user


def require_roles(*allowed_roles: str):
    normalized_roles = {role.strip().casefold() for role in allowed_roles}

    if not normalized_roles or "" in normalized_roles:
        raise ValueError("At least one valid role must be specified")

    def role_checker(
        current_user: User = Depends(get_current_user)
    ):
        if current_user.role.name.strip().casefold() not in normalized_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource"
            )

        return current_user

    return role_checker


def require_role(required_role: str):
    return require_roles(required_role)
