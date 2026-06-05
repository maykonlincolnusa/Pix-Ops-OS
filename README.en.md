# PixOps OS

**Real-Time Payment Operations, Reconciliation & Anti-Fraud Platform**

PixOps OS is a real-time payment operations platform for Brazilian businesses, connecting Pix, banks, card machines, PSPs, and acquirers into a unified event-driven ledger for reconciliation, anti-fraud, and financial intelligence.

## Why International Companies Operate in Brazil

International companies operate in Brazil because the country offers:

- one of the largest payment volumes globally,
- strong digital adoption, especially with Pix,
- a large SMB and enterprise customer base with reconciliation pain,
- a fragmented provider landscape that requires orchestration.

For global players, Brazil is strategic: high scale, high operational complexity, and clear demand for real-time payment intelligence.

## Product Positioning

- Not a bank and not a financial institution replacement.
- Operational layer above banks, PSPs, acquirers, and gateways.
- Does not claim 100% fraud prevention.
- Focuses on reducing operational fraud, fake proof fraud, human error, and reconciliation gaps.

## MVP Scope

- multi-tenant onboarding (tenant, company, store, operator, cashier),
- sale -> payment intent -> Pix charge -> webhook -> reconciliation flow,
- append-only event store with hash chain,
- basic double-entry ledger entries,
- initial anti-fraud rule engine,
- real-time operations dashboard,
- developer API for third parties.

## Quick Start

```bash
docker compose up --build
```

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Technical Docs

- [Architecture](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/architecture.md)
- [API](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/api.md)
- [Event Catalog](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/event-catalog.md)
- [Security](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/security.md)
