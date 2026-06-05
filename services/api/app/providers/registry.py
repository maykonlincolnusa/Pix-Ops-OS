from app.providers.adapters.mock_card import MockCardProvider
from app.providers.adapters.mock_pix import MockPixProvider
from app.providers.base import PaymentProviderAdapter


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, PaymentProviderAdapter] = {
            "mock_pix": MockPixProvider(),
            "mock_card": MockCardProvider(),
            # Real provider adapters prepared for future implementation:
            # openpix, efi, mercado_pago, cielo, stone, pagarme, bb, itau, inter, sicredi
        }

    def get(self, name: str) -> PaymentProviderAdapter:
        key = name.strip().lower()
        provider = self._providers.get(key)
        if not provider:
            raise KeyError(f"Provider adapter '{name}' is not configured.")
        return provider


provider_registry = ProviderRegistry()
