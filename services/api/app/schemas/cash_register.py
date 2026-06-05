from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class CashRegisterCreate(BaseModel):
    tenant_id: str
    company_id: str
    store_id: str
    operator_id: str | None = None
    code: str = Field(min_length=2, max_length=50)


class CashRegisterRead(BaseSchema):
    id: str
    tenant_id: str
    company_id: str
    store_id: str
    operator_id: str | None
    code: str
    status: str
    created_at: datetime
