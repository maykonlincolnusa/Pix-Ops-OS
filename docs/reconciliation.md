# Reconciliation

## Inputs
- Sale esperada
- PaymentIntent/PixCharge
- WebhookEvent normalizado
- Ledger entries

## States
- matched
- pending
- expired
- underpaid
- overpaid
- duplicate
- suspicious
- refunded
- reversed
- provider_error
- manual_review
- orphan_payment

## Rules (MVP)
- `txid` + valor igual => matched
- `txid` + valor menor => underpaid
- `txid` + valor maior => overpaid
- Webhook duplicado => duplicate_event_ignored
- Pagamento sem venda => orphan_payment

## Output
- `reconciliation_records`
- Eventos no `event_store`
- Alertas antifraude quando divergente
