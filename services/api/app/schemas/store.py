from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class StoreCreate(BaseModel):
    tenant_id: str
    company_id: str
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=50)


class StoreRead(BaseSchema):
    id: str
    tenant_id: str
    company_id: str
    name: str
    code: str
    created_at: datetime
