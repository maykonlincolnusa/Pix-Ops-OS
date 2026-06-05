import hashlib
import json
from datetime import datetime, timezone


def ensure_utc_iso(value: datetime | None) -> str:
    if not value:
        value = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_event_store_hash(
    *,
    previous_hash: str | None,
    payload: dict,
    occurred_at: datetime | None,
    aggregate_id: str,
    event_type: str,
) -> str:
    base = (
        f"{previous_hash or ''}"
        f"{canonical_json(payload)}"
        f"{ensure_utc_iso(occurred_at)}"
        f"{aggregate_id}"
        f"{event_type}"
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
