# Database Model

## Core Multi-tenant
- tenants
- companies
- stores
- operators
- cash_registers
- users
- refresh_tokens
- api_credentials
- provider_connections

## Payments
- sales
- payment_intents
- pix_charges
- card_transactions
- bank_transactions

## Event Sourcing / Audit
- event_store (append-only)
- webhook_events
- audit_events

## Ledger / Reconciliation / Fraud
- ledger_entries
- reconciliation_records
- reconciliation_batches
- fraud_flags
- fraud_alerts
- manual_review_cases
- notification_outbox
- agent_runs
- agent_tasks
- cash_closure_reports

## Hash Chain
`current_hash = SHA256(previous_hash + canonical_payload + occurred_at + aggregate_id + event_type)`

## Financial Integrity Notes
- `ledger_entries.source_event_id` is required for new ledger records.
- `notification_outbox.correlation_id` links operational alerts to the event/payment timeline.
- `reconciliation_records.company_id` is nullable to support orphan provider payments before sale/company resolution.
