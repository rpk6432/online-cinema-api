import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


def _validate_password(password: str) -> str:
    if len(password) < 8:
        msg = "Password must be at least 8 characters"
        raise ValueError(msg)
    if not re.search(r"[A-Z]", password):
        msg = "Password must contain at least one uppercase letter"
        raise ValueError(msg)
    if not re.search(r"[a-z]", password):
        msg = "Password must contain at least one lowercase letter"
        raise ValueError(msg)
    if not re.search(r"\d", password):
        msg = "Password must contain at least one digit"
        raise ValueError(msg)
    return password


# Requests


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)


class ActivateRequest(BaseModel):
    token: str


class ResendActivationRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)


# Responses


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    group_name: str
    created_at: datetime

    model_config = {"from_attributes": True}

