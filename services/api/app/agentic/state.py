from typing import Any, Literal, TypedDict


class AgenticState(TypedDict, total=False):
    tenant_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    provider: str | None
    correlation_id: str
    causation_id: str | None
    trace_id: str | None
    source_event_id: str | None
    payload: dict[str, Any]
    metadata: dict[str, Any]
    decision: str
    confidence_score: float
    reasoning_summary: str
    status: Literal["ok", "blocked", "failed", "pending"]
    next_route: str
    payment_intent_id: str | None
    sale_id: str | None
    reconciliation_status: str | None
    risk_severity: str | None
    output_event_type: str | None
    output_event_id: str | None
    provider_verified: bool
    needs_manual_review: bool
    review_after_notification: bool
    decisions: list[dict[str, Any]]
