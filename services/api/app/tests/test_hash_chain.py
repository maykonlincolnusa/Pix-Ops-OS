from datetime import datetime, timezone

from app.services.hash_chain import build_event_store_hash


def test_hash_chain_changes_when_payload_changes() -> None:
    ts = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    hash_a = build_event_store_hash(
        previous_hash="abc",
        payload={"amount_cents": 1000},
        occurred_at=ts,
        aggregate_id="sale-1",
        event_type="sale.created",
    )
    hash_b = build_event_store_hash(
        previous_hash="abc",
        payload={"amount_cents": 900},
        occurred_at=ts,
        aggregate_id="sale-1",
        event_type="sale.created",
    )
    assert hash_a != hash_b
