from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import LedgerEvent
from app.services.event_bus import event_bus
from app.services.hash_chain import build_event_hash


def append_ledger_event(
    db: Session,
    *,
    company_id: str,
    store_id: str | None,
    sale_id: str | None,
    source: str,
    event_type: str,
    reference_id: str | None = None,
    amount_cents: int | None = None,
    occurred_at: datetime | None = None,
    payload: dict[str, Any] | None = None,
) -> LedgerEvent:
    if payload is None:
        payload = {}
    occurred_at = occurred_at or datetime.now(timezone.utc)

    last_event = db.scalar(
        select(LedgerEvent)
        .where(LedgerEvent.company_id == company_id)
        .order_by(desc(LedgerEvent.sequence_no))
        .limit(1)
    )
    sequence_no = 1 if not last_event else last_event.sequence_no + 1
    prev_hash = None if not last_event else last_event.event_hash

    event_hash = build_event_hash(
        prev_hash=prev_hash,
        company_id=company_id,
        sequence_no=sequence_no,
        event_type=event_type,
        source=source,
        reference_id=reference_id,
        amount_cents=amount_cents,
        occurred_at=occurred_at,
        payload=payload,
    )

    event = LedgerEvent(
        company_id=company_id,
        store_id=store_id,
        sale_id=sale_id,
        sequence_no=sequence_no,
        source=source,
        event_type=event_type,
        reference_id=reference_id,
        amount_cents=amount_cents,
        payload=payload,
        prev_hash=prev_hash,
        event_hash=event_hash,
        occurred_at=occurred_at,
    )
    db.add(event)
    db.flush()

    event_bus.publish_company_event(
        company_id=company_id,
        event={
            "event_id": event.event_id,
            "sequence_no": event.sequence_no,
            "source": event.source,
            "event_type": event.event_type,
            "reference_id": event.reference_id,
            "amount_cents": event.amount_cents,
            "occurred_at": event.occurred_at.isoformat(),
            "event_hash": event.event_hash,
        },
    )
    return event
