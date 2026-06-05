import pytest

from app.db.models import PaymentIntentStatus, ReconciliationStatus, SaleStatus
from app.services.event_catalog import EventType
from app.services.ledger import create_double_entry


def test_state_machine_contains_block_and_review_states() -> None:
    assert SaleStatus.BLOCKED.value == "blocked"
    assert SaleStatus.MANUAL_REVIEW_REQUIRED.value == "manual_review_required"
    assert PaymentIntentStatus.RECONCILING.value == "reconciling"
    assert PaymentIntentStatus.MANUAL_REVIEW_REQUIRED.value == "manual_review_required"
    assert ReconciliationStatus.LATE_PAYMENT.value == "late_payment"


def test_event_catalog_contains_financial_control_events() -> None:
    assert EventType.SALE_RELEASE_BLOCKED.value == "sale.release_blocked"
    assert EventType.MANUAL_REVIEW_REQUIRED.value == "manual_review.required"
    assert EventType.PAYMENT_TIMEOUT_DETECTED.value == "payment.timeout_detected"


def test_ledger_requires_source_event_id() -> None:
    with pytest.raises(ValueError, match="source_event_id"):
        create_double_entry(
            None,  # type: ignore[arg-type]
            tenant_id="tenant-1",
            transaction_id="payment-1",
            amount_cents=10000,
            currency="BRL",
            provider="mock_pix",
            source_event_id="",
            debit_account_id="cash_in_transit",
            credit_account_id="sales_revenue",
        )
