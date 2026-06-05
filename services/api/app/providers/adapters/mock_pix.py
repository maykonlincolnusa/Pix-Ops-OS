from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.providers.base import PaymentProviderAdapter


class MockPixProvider(PaymentProviderAdapter):
    provider_name = "mock_pix"

    def create_pix_charge(self, payload: dict) -> dict:
        txid = uuid4().hex[:30].upper()
        amount_cents = int(payload["amount_cents"])
        expires_in = int(payload.get("expires_in_minutes", 20))
        emv = (
            "00020126360014BR.GOV.BCB.PIX01"
            f"{len(payload['pix_key']):02d}{payload['pix_key']}"
            "520400005303986"
            f"540{len(f'{amount_cents/100:.2f}'):02d}{amount_cents/100:.2f}"
            "5802BR5925PIXOPS OS MOCK PROVIDER6008SAOPAULO62070503***6304ABCD"
        )
        return {
            "provider_charge_id": f"mock_{uuid4().hex[:16]}",
            "txid": txid,
            "location_id": f"loc_{uuid4().hex[:12]}",
            "emv_payload": emv,
            "qr_code_url": f"https://mock.pixops.local/qr/{txid}",
            "status": "created",
            "amount_cents": amount_cents,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=expires_in)).isoformat(),
        }

    def get_pix_charge(self, charge_id: str) -> dict:
        return {"id": charge_id, "status": "created"}

    def cancel_pix_charge(self, charge_id: str) -> dict:
        return {"id": charge_id, "status": "cancelled"}

    def refund_pix(self, charge_id: str, payload: dict) -> dict:
        return {"id": charge_id, "status": "refunded", "amount_cents": payload.get("amount_cents")}

    def parse_webhook(self, payload: dict, channel: str) -> dict:
        if channel == "pix":
            return {
                "external_event_id": payload.get("external_event_id") or payload.get("end_to_end_id"),
                "event_type": payload.get("event_type", "pix.payment.received"),
                "txid": payload.get("txid"),
                "end_to_end_id": payload.get("end_to_end_id"),
                "amount_cents": int(payload.get("amount_cents", 0)),
                "paid_at": payload.get("paid_at"),
                "status": payload.get("status", "confirmed"),
                "metadata": payload.get("metadata", {}),
            }
        return {
            "external_event_id": payload.get("external_event_id") or uuid4().hex,
            "event_type": payload.get("event_type", f"{channel}.event.received"),
            "metadata": payload,
        }

    def verify_webhook_signature(self, payload: bytes, signature: str | None, headers: dict[str, str]) -> bool:
        # Mock provider accepts a deterministic signature for testing.
        expected = "mock-valid-signature"
        return signature == expected or headers.get("x-mock-signature") == expected

    def create_card_payment(self, payload: dict) -> dict:
        return {
            "transaction_id": f"card_{uuid4().hex[:18]}",
            "status": "authorized",
            "nsu": payload.get("nsu") or uuid4().hex[:10].upper(),
            "authorization_code": uuid4().hex[:6].upper(),
            "amount_cents": payload.get("amount_cents", 0),
        }

    def get_card_transaction(self, transaction_id: str) -> dict:
        return {"transaction_id": transaction_id, "status": "authorized"}

    def list_bank_transactions(self, payload: dict) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        return [
            {
                "external_id": f"bank_{uuid4().hex[:14]}",
                "amount": 100.0,
                "direction": "in",
                "description": "Mock incoming transfer",
                "posted_at": now,
                "status": "posted",
            }
        ]
