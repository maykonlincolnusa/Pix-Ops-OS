# Security

## Controls in MVP
- Tenant isolation by `tenant_id`.
- Password hashing with bcrypt.
- JWT access + refresh token.
- RBAC roles: owner, admin, manager, cashier, auditor, developer.
- Environment API key for administrative/demo routes.
- Webhook signature validation for mock provider and extension point for real providers.
- Webhook idempotency by `external_event_id`.
- Event Store append-only by application contract with hash chain.
- Audit events for auth and agent decisions.
- `agent_runs` for every agent execution.
- `notification_outbox.correlation_id` for operational traceability.
- `ledger_entries.source_event_id` required for new financial ledger entries.
- Sale release blocked on timeout, mismatch and manual release attempt.

## LGPD by Design
- Minimize personal data collection.
- Do not store CVV or full card PAN.
- Do not log secrets or provider tokens.
- Avoid sensitive payloads in structured logs.
- Keep provider credentials encrypted before production usage.

## Required Production Hardening
- KMS/Vault for provider credentials.
- JWT key rotation.
- Replay protection with nonce/timestamp and expiration window per provider.
- Rate limiting by tenant and endpoint.
- Payload masking/DLP in observability pipelines.
- Retention and anonymization policy for LGPD.
- Webhook IP allowlists where supported by provider.
- Sentry or equivalent error monitoring with secret scrubbing.
