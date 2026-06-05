from datetime import datetime

from app.schemas.common import BaseSchema


class EventStoreRead(BaseSchema):
    id: int
    tenant_id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    event_version: int
    event_id: str
    correlation_id: str | None
    causation_id: str | None
    idempotency_key: str | None
    source: str
    provider: str | None
    payload_json: dict
    metadata_json: dict
    previous_hash: str | None
    current_hash: str
    occurred_at: datetime
    recorded_at: datetime
    actor_type: str | None
    actor_id: str | None
    ip_address: str | None
    user_agent: str | None
