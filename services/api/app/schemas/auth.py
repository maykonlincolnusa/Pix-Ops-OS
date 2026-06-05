from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import BaseSchema


class RegisterRequest(BaseModel):
    tenant_id: str
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    role: str = "manager"


class LoginRequest(BaseModel):
    tenant_id: str
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserProfile(BaseSchema):
    id: str
    tenant_id: str
    email: EmailStr
    full_name: str
    role: str
    status: str
    created_at: datetime
