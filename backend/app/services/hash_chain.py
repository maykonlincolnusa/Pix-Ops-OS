import hashlib
import json
from datetime import datetime, timezone


def ensure_utc_iso(value: datetime | None) -> str:
    if not value:
        value = datetime.now(timezone.utc)
    if not value.tzinfo:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def build_event_hash(
    prev_hash: str | None,
    company_id: str,
    sequence_no: int,
    event_type: str,
    source: str,
    reference_id: str | None,
    amount_cents: int | None,
    occurred_at: datetime | None,
    payload: dict,
) -> str:
    payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    base = "|".join(
        [
            prev_hash or "",
            company_id,
            str(sequence_no),
            event_type,
            source,
            reference_id or "",
            "" if amount_cents is None else str(amount_cents),
            ensure_utc_iso(occurred_at),
            payload_text,
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
