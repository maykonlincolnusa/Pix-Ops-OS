from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class SaleCreate(BaseModel):
    tenant_id: str
    company_id: str
    store_id: str
    cash_register_id: str | None = None
    operator_id: str | None = None
    external_ref: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=240)
    expected_amount_cents: int = Field(gt=0, le=500000000)
    expected_method: str = Field(default="PIX", max_length=40)


class SaleRead(BaseSchema):
    id: str
    tenant_id: str
    company_id: str
    store_id: str
    cash_register_id: str | None
    operator_id: str | None
    external_ref: str
    description: str | None
    expected_amount_cents: int
    currency: str
    expected_method: str
    status: str
    opened_at: datetime
    paid_at: datetime | None
