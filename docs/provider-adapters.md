# Provider Adapters

## Implemented in MVP
- MockPixProvider
- MockCardProvider

## Interface
PaymentProviderAdapter:
- create_pix_charge()
- get_pix_charge()
- cancel_pix_charge()
- refund_pix()
- parse_webhook()
- verify_webhook_signature()
- create_card_payment()
- get_card_transaction()
- list_bank_transactions()

## Planned (Scaffold Ready)
- OpenPix/Woovi
- Efí/Gerencianet
- Mercado Pago
- Cielo
- Stone/Pagar.me
- Banco do Brasil / Itaú / Inter / Sicredi
- Open Finance Adapter (consent + payment initiation)

## Mapping Notes
- Normalizar eventos por provider para payload interno canônico.
- Sempre mapear `txid`, `external_event_id`, `status`, `amount`, `occurred_at`.
- Assinatura webhook validada antes de processamento financeiro.
