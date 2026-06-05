from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class OperatorCreate(BaseModel):
    tenant_id: str
    company_id: str
    store_id: str | None = None
    full_name: str = Field(min_length=2, max_length=160)
    document: str | None = Field(default=None, max_length=20)


class OperatorRead(BaseSchema):
    id: str
    tenant_id: str
    company_id: str
    store_id: str | None
    full_name: str
    document: str | None
    active: bool
    created_at: datetime
