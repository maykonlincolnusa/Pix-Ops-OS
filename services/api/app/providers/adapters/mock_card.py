from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.providers.base import PaymentProviderAdapter


class MockCardProvider(PaymentProviderAdapter):
    provider_name = "mock_card"

    def create_pix_charge(self, payload: dict) -> dict:
        raise NotImplementedError("MockCardProvider does not create Pix charges.")

    def get_pix_charge(self, charge_id: str) -> dict:
        raise NotImplementedError("MockCardProvider does not manage Pix charges.")

    def cancel_pix_charge(self, charge_id: str) -> dict:
        raise NotImplementedError("MockCardProvider does not manage Pix charges.")

    def refund_pix(self, charge_id: str, payload: dict) -> dict:
        raise NotImplementedError("MockCardProvider does not manage Pix charges.")

    def parse_webhook(self, payload: dict, channel: str) -> dict:
        return {
            "external_event_id": payload.get("external_event_id") or payload.get("nsu") or uuid4().hex,
            "event_type": payload.get("event_type", "card.transaction.authorized"),
            "status": payload.get("status", "authorized"),
            "nsu": payload.get("nsu") or uuid4().hex[:10].upper(),
            "authorization_code": payload.get("authorization_code") or uuid4().hex[:6].upper(),
            "amount_cents": int(payload.get("amount_cents", 0)),
            "occurred_at": payload.get("occurred_at") or datetime.now(timezone.utc).isoformat(),
        }

    def verify_webhook_signature(self, payload: bytes, signature: str | None, headers: dict[str, str]) -> bool:
        return signature == "mock-valid-signature" or headers.get("x-mock-signature") == "mock-valid-signature"

    def create_card_payment(self, payload: dict) -> dict:
        return {
            "transaction_id": f"card_{uuid4().hex[:16]}",
            "status": payload.get("simulate_status", "authorized"),
            "nsu": payload.get("nsu") or uuid4().hex[:10].upper(),
            "authorization_code": uuid4().hex[:6].upper(),
            "amount_cents": int(payload.get("amount_cents", 0)),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_card_transaction(self, transaction_id: str) -> dict:
        return {"transaction_id": transaction_id, "status": "captured"}

    def list_bank_transactions(self, payload: dict) -> list[dict]:
        return []
