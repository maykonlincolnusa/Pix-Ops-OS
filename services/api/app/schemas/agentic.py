from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class AgenticEventIn(BaseModel):
    tenant_id: str
    event_type: str
    aggregate_type: str = "payment"
    aggregate_id: str
    source_event_id: str | None = None
    correlation_id: str
    causation_id: str | None = None
    trace_id: str | None = None
    provider: str | None = None
    payload: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class AgentRunRead(BaseSchema):
    id: str
    tenant_id: str
    correlation_id: str
    causation_id: str | None
    trace_id: str | None
    agent_name: str
    input_event_id: str | None
    output_event_id: str | None
    status: str
    decision: str
    reasoning_summary: str | None
    confidence_score: float | None
    langsmith_trace_id: str | None
    duration_ms: int | None
    created_at: datetime


class AgentTaskRead(BaseSchema):
    id: str
    tenant_id: str
    correlation_id: str | None
    causation_id: str | None
    trace_id: str | None
    agent_name: str
    task_type: str
    status: str
    priority: str
    due_at: datetime | None
    locked_at: datetime | None
    completed_at: datetime | None
    payload_json: dict
    created_at: datetime


class NotificationOutboxRead(BaseSchema):
    id: str
    tenant_id: str
    correlation_id: str | None
    channel: str
    recipient: str
    severity: str
    subject: str
    message: str
    status: str
    attempts: int
    next_retry_at: datetime | None
    created_at: datetime
    sent_at: datetime | None


class ManualReviewCaseRead(BaseSchema):
    id: str
    tenant_id: str
    sale_id: str | None
    payment_intent_id: str | None
    fraud_alert_id: str | None
    status: str
    severity: str
    summary: str
    recommendation: str
    assigned_to: str | None
    created_at: datetime
    resolved_at: datetime | None


class AgenticRunResponse(BaseSchema):
    status: str
    correlation_id: str
    trace_id: str | None
    final_event_type: str | None
    decisions: list[dict]
