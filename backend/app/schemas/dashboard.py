from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.common import BaseSchema


class LedgerEventItem(BaseSchema):
    event_id: str
    sequence_no: int
    source: str
    event_type: str
    reference_id: str | None
    amount_cents: int | None
    occurred_at: datetime
    event_hash: str


class DashboardMetrics(BaseSchema):
    company_id: str
    business_date: date
    total_sales: int
    paid_sales: int
    pending_sales: int
    divergent_sales: int
    expected_total_cents: int
    received_total_cents: int
    open_fraud_flags: int
    latest_events: list[LedgerEventItem]


class CashClosureSummary(BaseSchema):
    company_id: str
    store_id: str
    business_date: date
    totals: dict
    divergences: list[dict]
    recommendations: list[str]


class AISummaryResponse(BaseSchema):
    company_id: str
    business_date: date
    summary: str
    risk_level: str
    action_items: list[str]


class DashboardQuery(BaseModel):
    company_id: str
