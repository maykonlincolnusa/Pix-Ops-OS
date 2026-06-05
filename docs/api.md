# API

## Auth
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh

## Setup
- POST /api/v1/setup/tenants
- GET /api/v1/setup/tenants
- POST /api/v1/setup/companies
- GET /api/v1/setup/companies?tenant_id=
- POST /api/v1/setup/stores
- GET /api/v1/setup/stores?tenant_id=&company_id=
- POST /api/v1/setup/operators
- GET /api/v1/setup/operators?tenant_id=&company_id=
- POST /api/v1/setup/cash-registers
- GET /api/v1/setup/cash-registers?tenant_id=&company_id=

## Payments
- POST /api/v1/payments/sales
- GET /api/v1/payments/sales
- POST /api/v1/payments/pix/charges
- GET /api/v1/payments/pix/charges/{id}
- POST /api/v1/payments/pix/webhooks/confirmation
- POST /api/v1/payments/sales/{sale_id}/manual-release

## Generic Webhooks
- POST /api/v1/webhooks/{provider}/pix
- POST /api/v1/webhooks/{provider}/card
- POST /api/v1/webhooks/{provider}/bank
- GET /api/v1/webhooks/events

## Dashboard
- GET /api/v1/dashboard/metrics
- GET /api/v1/dashboard/events
- GET /api/v1/dashboard/ledger
- GET /api/v1/dashboard/divergences
- GET /api/v1/dashboard/fraud-alerts
- GET /api/v1/dashboard/closeout
- GET /api/v1/dashboard/ai-summary
- POST /api/v1/dashboard/ai-query

## AI
- GET /api/v1/ai/daily-summary
- POST /api/v1/ai/query

## Agentic Layer
- POST /api/v1/agentic/run
- POST /api/v1/agentic/watchdog/run
- GET /api/v1/agentic/runs
- GET /api/v1/agentic/tasks
- GET /api/v1/agentic/notifications
- GET /api/v1/agentic/manual-review-cases
- POST /api/v1/agentic/manual-review-cases/{case_id}/actions

## Developer API
- POST /api/v1/sales
- GET /api/v1/sales
- GET /api/v1/sales/{id}
- POST /api/v1/payment-intents
- GET /api/v1/payment-intents/{id}
- POST /api/v1/pix/charges
- GET /api/v1/pix/charges/{id}
- GET /api/v1/payments/{id}
- GET /api/v1/events
- GET /api/v1/ledger
- GET /api/v1/reconciliation
- GET /api/v1/fraud-alerts
- GET /api/v1/manual-review-cases
- GET /api/v1/notifications
- GET /api/v1/dashboard

## Auth Headers (MVP)
- X-API-Key: master API key for administrative/demo routes.
- X-Tenant-ID: required for generic webhooks.
