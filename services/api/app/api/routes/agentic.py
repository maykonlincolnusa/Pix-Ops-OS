from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agentic.router import run_agent_router
from app.api.deps import DBSession, MasterApiKeyDep
from app.db.models import (
    AgentRun,
    AgentTask,
    FraudStatus,
    ManualReviewCase,
    NotificationOutbox,
    PaymentIntent,
    PaymentIntentStatus,
)
from app.schemas.agentic import (
    AgenticEventIn,
    AgenticRunResponse,
    AgentRunRead,
    AgentTaskRead,
    ManualReviewCaseRead,
    NotificationOutboxRead,
)
from app.services.event_catalog import EventType
from app.services.ledger import append_event

router = APIRouter(prefix="/agentic", tags=["agentic"])


class ManualReviewActionPayload(BaseModel):
    action: str = Field(pattern="^(resolve|escalate|ignore|request_recheck)$")
    note: str | None = Field(default=None, max_length=400)
    actor_id: str | None = Field(default=None, max_length=64)


@router.post("/run", response_model=AgenticRunResponse, status_code=status.HTTP_202_ACCEPTED)
def run_agentic_event(_: MasterApiKeyDep, payload: AgenticEventIn, db: DBSession) -> AgenticRunResponse:
    final_state = run_agent_router(
        db,
        tenant_id=payload.tenant_id,
        event_type=payload.event_type,
        aggregate_type=payload.aggregate_type,
        aggregate_id=payload.aggregate_id,
        payload=payload.payload,
        metadata=payload.metadata,
        correlation_id=payload.correlation_id,
        causation_id=payload.causation_id,
        trace_id=payload.trace_id,
        provider=payload.provider,
        source_event_id=payload.source_event_id,
    )
    db.commit()
    return AgenticRunResponse(
        status=final_state.get("status", "ok"),
        correlation_id=final_state["correlation_id"],
        trace_id=final_state.get("trace_id"),
        final_event_type=final_state.get("output_event_type"),
        decisions=final_state.get("decisions", []),
    )


@router.post("/watchdog/run")
def run_timeout_watchdog(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict:
    payment_intents = db.scalars(
        select(PaymentIntent)
        .where(
            PaymentIntent.tenant_id == tenant_id,
            PaymentIntent.status.in_(
                [
                    PaymentIntentStatus.AWAITING_PAYMENT.value,
                    PaymentIntentStatus.CREATED.value,
                ]
            ),
        )
        .order_by(PaymentIntent.created_at.asc())
        .limit(limit)
    ).all()

    total = 0
    pending = 0
    timed_out = 0
    for payment_intent in payment_intents:
        due_at = payment_intent.expires_at or datetime.now(timezone.utc)
        final_state = run_agent_router(
            db,
            tenant_id=tenant_id,
            event_type=EventType.PAYMENT_AWAITING_CONFIRMATION.value,
            aggregate_type="payment_intent",
            aggregate_id=payment_intent.id,
            payload={
                "payment_intent_id": payment_intent.id,
                "sale_id": payment_intent.sale_id,
                "provider": payment_intent.provider,
                "due_at": due_at.isoformat(),
            },
            metadata={"watchdog": "scan"},
            correlation_id=payment_intent.id,
            provider=payment_intent.provider,
        )
        total += 1
        if final_state.get("event_type") == EventType.PAYMENT_TIMEOUT_DETECTED.value:
            timed_out += 1
        if final_state.get("status") == "pending":
            pending += 1

    db.commit()
    return {
        "tenant_id": tenant_id,
        "processed": total,
        "pending": pending,
        "timed_out": timed_out,
    }


@router.get("/runs", response_model=list[AgentRunRead])
def list_agent_runs(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    correlation_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[AgentRun]:
    query = select(AgentRun).where(AgentRun.tenant_id == tenant_id)
    if correlation_id:
        query = query.where(AgentRun.correlation_id == correlation_id)
    return db.scalars(query.order_by(AgentRun.created_at.desc()).limit(limit)).all()


@router.get("/tasks", response_model=list[AgentTaskRead])
def list_agent_tasks(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[AgentTask]:
    query = select(AgentTask).where(AgentTask.tenant_id == tenant_id)
    if status_filter:
        query = query.where(AgentTask.status == status_filter)
    return db.scalars(query.order_by(AgentTask.created_at.desc()).limit(limit)).all()


@router.get("/notifications", response_model=list[NotificationOutboxRead])
def list_notifications(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[NotificationOutbox]:
    query = select(NotificationOutbox).where(NotificationOutbox.tenant_id == tenant_id)
    if status_filter:
        query = query.where(NotificationOutbox.status == status_filter)
    return db.scalars(query.order_by(NotificationOutbox.created_at.desc()).limit(limit)).all()


@router.get("/manual-review-cases", response_model=list[ManualReviewCaseRead])
def list_manual_review_cases(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[ManualReviewCase]:
    query = select(ManualReviewCase).where(ManualReviewCase.tenant_id == tenant_id)
    if status_filter:
        query = query.where(ManualReviewCase.status == status_filter)
    return db.scalars(query.order_by(ManualReviewCase.created_at.desc()).limit(limit)).all()


@router.post("/manual-review-cases/{case_id}/actions")
def act_on_manual_review_case(
    case_id: str,
    payload: ManualReviewActionPayload,
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
) -> dict:
    case = db.scalar(
        select(ManualReviewCase).where(
            ManualReviewCase.id == case_id,
            ManualReviewCase.tenant_id == tenant_id,
        )
    )
    if not case:
        raise HTTPException(status_code=404, detail="Manual review case not found.")

    mapping = {
        "resolve": ("resolved", EventType.FRAUD_ALERT_RESOLVED.value),
        "escalate": ("escalated", EventType.FRAUD_ALERT_ESCALATED.value),
        "ignore": (FraudStatus.IGNORED.value, EventType.FRAUD_ALERT_RESOLVED.value),
        "request_recheck": ("recheck_requested", EventType.AI_QUERY_EXECUTED.value),
    }
    status_value, event_type = mapping[payload.action]
    case.status = status_value
    if payload.action in {"resolve", "ignore"}:
        case.resolved_at = datetime.now(timezone.utc)
    db.add(case)

    append_event(
        db,
        tenant_id=tenant_id,
        aggregate_type="manual_review_case",
        aggregate_id=case.id,
        event_type=event_type,
        payload={
            "action": payload.action,
            "note": payload.note,
            "actor_id": payload.actor_id,
            "case_status": case.status,
            "fraud_alert_id": case.fraud_alert_id,
        },
        source="agentic.manual_review",
        correlation_id=case.payment_intent_id or case.sale_id or case.id,
        actor_type="user" if payload.actor_id else None,
        actor_id=payload.actor_id,
    )
    db.commit()
    return {"case_id": case.id, "status": case.status}
