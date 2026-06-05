# Architecture

## Context
PixOps OS opera como camada operacional acima de bancos/PSPs/adquirentes.

## Mermaid
```mermaid
flowchart TB
  subgraph Channels
    POS[PDV/Caixa]
    WEB[Dashboard Web/PWA]
    EXT[ERPs e terceiros API]
  end

  subgraph Core API
    AUTH[Auth + RBAC]
    TENANT[Tenant Guard]
    PAY[Payments + Pix Charge Engine]
    WH[Webhook Receiver]
    RECON[Reconciliation Engine]
    FRAUD[Anti-Fraud Rules]
    AI[AI Copilot Rules]
  end

  subgraph Adapters
    MPX[MockPix]
    MCD[MockCard]
    RLS[Real Adapters Ready]
  end

  subgraph Data
    ES[(event_store)]
    LED[(ledger_entries)]
    DOM[(Domain tables)]
    RED[(Redis)]
  end

  POS --> PAY
  WEB --> AUTH
  WEB --> PAY
  EXT --> PAY
  WH --> PAY
  PAY --> RECON
  PAY --> FRAUD
  PAY --> AI
  PAY --> ES
  PAY --> LED
  PAY --> DOM
  PAY --> RED
  PAY --> MPX
  PAY --> MCD
  PAY --> RLS
```

## Design Notes
- Event sourcing simplificado: eventos financeiros principais no `event_store`.
- Ledger orientado a double-entry quando pagamento é confirmado.
- Multi-tenant por `tenant_id` em todas as consultas de domínio.
- `webhook_events` armazena payload bruto antes do processamento.
