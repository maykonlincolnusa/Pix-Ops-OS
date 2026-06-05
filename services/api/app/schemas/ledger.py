from datetime import datetime

from app.schemas.common import BaseSchema


class LedgerEntryRead(BaseSchema):
    id: str
    tenant_id: str
    account_id: str
    transaction_id: str
    entry_type: str
    direction: str
    amount: float
    currency: str
    status: str
    provider: str | None
    source_event_id: str
    created_at: datetime
