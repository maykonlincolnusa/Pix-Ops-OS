from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentRun,
    AgentTask,
    ManualReviewCase,
    NotificationOutbox,
    PaymentIntent,
)
from app.services.audit import create_audit_event


def save_agent_run(
    db: Session,
    *,
    tenant_id: str,
    correlation_id: str,
    causation_id: str | None,
    trace_id: str | None,
    agent_name: str,
    input_event_id: str | None,
    output_event_id: str | None,
    status: str,
    decision: str,
    reasoning_summary: str | None,
    confidence_score: float | None,
    langsmith_trace_id: str | None,
    duration_ms: int | None,
    metadata: dict[str, Any] | None = None,
) -> AgentRun:
    run = AgentRun(
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        trace_id=trace_id,
        agent_name=agent_name,
        input_event_id=input_event_id,
        output_event_id=output_event_id,
        status=status,
        decision=decision,
        reasoning_summary=reasoning_summary,
        confidence_score=Decimal(str(confidence_score)) if confidence_score is not None else None,
        langsmith_trace_id=langsmith_trace_id,
        duration_ms=duration_ms,
        metadata_json=metadata or {},
    )
    db.add(run)
    db.flush()
    create_audit_event(
        db,
        tenant_id=tenant_id,
        actor_type="agent",
        actor_id=agent_name,
        action=f"agent.run.{agent_name}",
        target_type="agent_run",
        target_id=run.id,
        metadata={
            "decision": decision,
            "status": status,
            "correlation_id": correlation_id,
            "trace_id": trace_id,
        },
    )
    return run


def create_agent_task(
    db: Session,
    *,
    tenant_id: str,
    agent_name: str,
    task_type: str,
    priority: str,
    due_at: datetime | None,
    payload_json: dict[str, Any],
    correlation_id: str | None = None,
    causation_id: str | None = None,
    trace_id: str | None = None,
) -> AgentTask:
    task = AgentTask(
        tenant_id=tenant_id,
        agent_name=agent_name,
        task_type=task_type,
        status="pending",
        priority=priority,
        due_at=due_at,
        payload_json=payload_json,
        correlation_id=correlation_id,
        causation_id=causation_id,
        trace_id=trace_id,
    )
    db.add(task)
    db.flush()
    return task


def resolve_agent_task(db: Session, task: AgentTask) -> None:
    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)
    db.add(task)


def enqueue_notification(
    db: Session,
    *,
    tenant_id: str,
    correlation_id: str | None,
    channel: str,
    recipient: str,
    severity: str,
    subject: str,
    message: str,
) -> NotificationOutbox:
    item = NotificationOutbox(
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        channel=channel,
        recipient=recipient,
        severity=severity,
        subject=subject,
        message=message,
        status="pending",
        attempts=0,
    )
    db.add(item)
    db.flush()
    return item


def mark_notification_sent(db: Session, item: NotificationOutbox) -> None:
    item.status = "sent"
    item.sent_at = datetime.now(timezone.utc)
    item.attempts += 1
    db.add(item)


def create_manual_review_case(
    db: Session,
    *,
    tenant_id: str,
    sale_id: str | None,
    payment_intent_id: str | None,
    fraud_alert_id: str | None,
    severity: str,
    summary: str,
    recommendation: str,
) -> ManualReviewCase:
    case = ManualReviewCase(
        tenant_id=tenant_id,
        sale_id=sale_id,
        payment_intent_id=payment_intent_id,
        fraud_alert_id=fraud_alert_id,
        status="open",
        severity=severity,
        summary=summary,
        recommendation=recommendation,
    )
    db.add(case)
    db.flush()
    return case


def get_payment_intent_by_id(db: Session, tenant_id: str, payment_intent_id: str) -> PaymentIntent | None:
    return db.scalar(
        select(PaymentIntent).where(
            PaymentIntent.tenant_id == tenant_id,
            PaymentIntent.id == payment_intent_id,
        )
    )
