from app.services.event_catalog import EventType


def test_event_catalog_contains_pix_orphan() -> None:
    assert EventType.PIX_PAYMENT_ORPHAN_DETECTED.value == "pix.payment.orphan_detected"
