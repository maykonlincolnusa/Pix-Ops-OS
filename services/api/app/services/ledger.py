from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import EventStore, LedgerDirection, LedgerEntry, LedgerEntryType
from app.services.event_bus import event_bus
from app.services.hash_chain import build_event_store_hash


def append_event(
    db: Session,
    *,
    tenant_id: str,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    payload: dict[str, Any],
    source: str,
    provider: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> EventStore:
    occurred_at = occurred_at or datetime.now(timezone.utc)
    metadata = metadata or {}

    previous = db.scalar(
        select(EventStore)
        .where(EventStore.tenant_id == tenant_id)
        .order_by(desc(EventStore.id))
        .limit(1)
    )
    previous_hash = previous.current_hash if previous else None
    current_hash = build_event_store_hash(
        previous_hash=previous_hash,
        payload=payload,
        occurred_at=occurred_at,
        aggregate_id=aggregate_id,
        event_type=event_type,
    )

    event = EventStore(
        tenant_id=tenant_id,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        correlation_id=correlation_id,
        causation_id=causation_id,
        idempotency_key=idempotency_key,
        source=source,
        provider=provider,
        payload_json=payload,
        metadata_json=metadata,
        previous_hash=previous_hash,
        current_hash=current_hash,
        occurred_at=occurred_at,
        actor_type=actor_type,
        actor_id=actor_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(event)
    db.flush()

    event_bus.publish_tenant_event(
        tenant_id,
        {
            "event_id": event.event_id,
            "tenant_id": tenant_id,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "event_type": event_type,
            "occurred_at": event.occurred_at.isoformat(),
            "current_hash": event.current_hash,
        },
    )
    return event


def create_double_entry(
    db: Session,
    *,
    tenant_id: str,
    transaction_id: str,
    amount_cents: int,
    currency: str,
    provider: str,
    source_event_id: str,
    debit_account_id: str,
    credit_account_id: str,
    entry_type: LedgerEntryType = LedgerEntryType.SETTLED,
    status: str = "settled",
) -> list[LedgerEntry]:
    if not source_event_id:
        raise ValueError("Ledger entries require source_event_id.")

    amount = Decimal(amount_cents) / Decimal(100)
    debit = LedgerEntry(
        tenant_id=tenant_id,
        account_id=debit_account_id,
        transaction_id=transaction_id,
        entry_type=entry_type.value,
        direction=LedgerDirection.DEBIT.value,
        amount=amount,
        currency=currency,
        status=status,
        provider=provider,
        source_event_id=source_event_id,
    )
    credit = LedgerEntry(
        tenant_id=tenant_id,
        account_id=credit_account_id,
        transaction_id=transaction_id,
        entry_type=entry_type.value,
        direction=LedgerDirection.CREDIT.value,
        amount=amount,
        currency=currency,
        status=status,
        provider=provider,
        source_event_id=source_event_id,
    )
    db.add_all([debit, credit])
    db.flush()
    return [debit, credit]
