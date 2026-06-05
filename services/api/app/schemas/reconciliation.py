from datetime import datetime

from app.schemas.common import BaseSchema


class ReconciliationRecordRead(BaseSchema):
    id: str
    tenant_id: str
    company_id: str | None
    store_id: str | None
    sale_id: str | None
    txid: str | None
    expected_amount_cents: int | None
    received_amount_cents: int | None
    status: str
    reason: str
    created_at: datetime


class FraudFlagRead(BaseSchema):
    id: str
    tenant_id: str
    company_id: str
    store_id: str | None
    sale_id: str | None
    txid: str | None
    severity: str
    flag_type: str
    description: str
    status: str
    created_at: datetime
