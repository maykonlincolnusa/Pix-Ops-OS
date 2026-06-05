from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    document_number: str = Field(min_length=11, max_length=20)
    plan: str = Field(default="starter", max_length=40)


class TenantRead(BaseSchema):
    id: str
    name: str
    document_number: str
    plan: str
    status: str
    created_at: datetime
