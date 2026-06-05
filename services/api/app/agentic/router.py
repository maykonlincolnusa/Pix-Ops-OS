from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.agentic.graph import run_agentic_graph
from app.agentic.state import AgenticState
from app.services.event_catalog import EventType


SUPPORTED_ROUTES = {
    EventType.WEBHOOK_RECEIVED.value: "ProviderVerificationAgent",
    EventType.WEBHOOK_VERIFIED.value: "PaymentStateAgent",
    EventType.PAYMENT_STATE_CHECKED.value: "ReconciliationAgent",
    "reconciliation.matched": "LedgerAgent",
    EventType.RECONCILIATION_FAILED.value: "FraudDefenseAgent",
    EventType.PAYMENT_AWAITING_CONFIRMATION.value: "TimeoutWatchdogAgent",
    EventType.PAYMENT_TIMEOUT_DETECTED.value: "NotificationAgent",
    EventType.FRAUD_ALERT_CREATED.value: "HumanReviewAgent",
    EventType.LEDGER_ENTRY_CREATED.value: "NotificationAgent",
    EventType.CASHIER_SESSION_CLOSED.value: "ReportAgent",
}


def run_agent_router(
    db: Session,
    *,
    tenant_id: str,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict,
    metadata: dict | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    trace_id: str | None = None,
    provider: str | None = None,
    source_event_id: str | None = None,
) -> AgenticState:
    metadata = metadata or {}
    state: AgenticState = {
        "tenant_id": tenant_id,
        "event_type": event_type,
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "payload": payload,
        "metadata": metadata,
        "provider": provider,
        "correlation_id": correlation_id or str(uuid4()),
        "causation_id": causation_id,
        "trace_id": trace_id or str(uuid4()),
        "source_event_id": source_event_id,
        "status": "pending",
        "decision": "router_received",
        "reasoning_summary": "Agent router accepted event.",
        "confidence_score": 1.0,
        "decisions": [],
    }
    return run_agentic_graph(db, state)
