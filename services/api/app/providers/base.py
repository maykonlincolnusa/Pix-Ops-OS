from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PaymentProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    def create_pix_charge(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_pix_charge(self, charge_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def cancel_pix_charge(self, charge_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def refund_pix(self, charge_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def parse_webhook(self, payload: dict[str, Any], channel: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def verify_webhook_signature(
        self, payload: bytes, signature: str | None, headers: dict[str, str]
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def create_card_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_card_transaction(self, transaction_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_bank_transactions(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError
