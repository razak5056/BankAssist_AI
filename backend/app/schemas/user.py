from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal[
        "Customer",
        "L1 Support",
        "L2 Senior Support",
        "L3 Support Manager",
        "Admin",
    ]


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role_id: int
    is_active: bool

    class Config:
        from_attributes = True


class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool