# Reconciliation Engine

## Purpose

The Reconciliation Engine compares what PixOps OS expected to receive with what providers actually confirmed. It is the gate before `sale.paid` and final ledger confirmation.

## Inputs

- Sale: tenant, store, operator, cashier, amount, expected method and external reference.
- PaymentIntent: expected amount, received amount, provider, status and expiration.
- PixCharge/CardTransaction/BankTransaction: provider references such as `txid`, NSU, authorization code or external ID.
- WebhookEvent: raw payload, normalized payload, signature status and provider event ID.
- EventStore: correlation, causation and append-only audit trail.

## Classifications

- `matched`
- `pending`
- `expired`
- `underpaid`
- `overpaid`
- `duplicate`
- `orphan_payment`
- `late_payment`
- `suspicious`
- `manual_review_required`
- `provider_error`

## Core Rules

- `txid` matches and amount matches: `matched`.
- `txid` matches and amount is lower: `underpaid`.
- `txid` matches and amount is higher: `overpaid`.
- Known provider event received twice: `duplicate`.
- Unknown `txid` or no sale/payment intent context: `orphan_payment`.
- Provider event received after expiration: `late_payment`.
- Invalid signature or unknown provider: `provider_error` or fraud path.

## Payment Finalization Invariant

`sale.status = paid` is allowed only when:

- provider event is verified;
- idempotency is respected;
- tenant matches;
- provider matches;
- amount matches;
- reconciliation status is `matched`;
- ledger entries are created with `source_event_id`.

## Outputs

- `reconciliation_records`
- `event_store` events
- `ledger_entries` for matched payments
- `fraud_alerts` for mismatches or suspicious events
- `manual_review_cases` when human review is required
