# Architecture Audit

## 1. O que ja existe

PixOps OS ja tem uma base funcional de MVP com:

- Backend principal em `services/api` usando FastAPI, SQLAlchemy, PostgreSQL, Redis-ready, JWT/RBAC, tenant middleware, rate limiting e OpenTelemetry.
- Frontend principal em `apps/web` com Next.js, TypeScript, TailwindCSS, PWA manifest/service worker e dashboard operacional.
- Modelos de dominio para tenant, company, store, operator, cash register, sale, payment intent, Pix charge, card transaction, bank transaction, webhook event, event store, ledger, reconciliation, fraud, provider connection, API credential, device, report, agent runs, agent tasks, notifications e manual review.
- Event Store com hash chain tamper-evident via `previous_hash` e `current_hash`.
- Ledger com double-entry para pagamentos conciliados.
- Provider Connector Layer com interface generica e providers mockados (`MockPixProvider`, `MockCardProvider`).
- Webhook Receiver para Pix, card e bank, com payload bruto, assinatura mockada, idempotencia por `external_event_id` e envio para Agent Router.
- Camada agentic com LangGraph/LangChain, agentes de intake, verificacao, estado, reconciliacao, ledger, fraude, timeout, notificacao, human review e report.
- Documentacao inicial em `docs/` cobrindo arquitetura, API, eventos, banco, seguranca, observabilidade, providers, fraude, reconciliacao, roadmap e agentic architecture.
- Testes iniciais para hash chain e catalogo de eventos.

## 2. O que esta correto

- O principio central foi incorporado no desenho: pagamento nao deve ser confirmado sem evento validado, reconciliacao e ledger.
- `event_store` contem `tenant_id`, aggregate, event type, payload, metadata, correlation/causation, provider e hash chain.
- Webhooks ja sao salvos antes do processamento de negocio.
- `webhook_events` tem constraint unica por `tenant_id`, `provider`, `external_event_id`.
- O fluxo Pix mockado gera `txid`, QR/copiar e colar, charge e payment intent.
- O Agentic Layer registra `agent_runs` e `audit_events`, sem persistir chain-of-thought.
- Provider adapters estao isolados por interface, o que evita acoplar core de pagamentos a um PSP especifico.
- O frontend permite demonstrar criacao de venda, QR Pix, webhook simulado, eventos, ledger, fraude e fechamento.

## 3. O que esta incompleto

- Ha duas arvores antigas/paralelas (`backend/` e `frontend/`) alem de `services/api` e `apps/web`; isso cria ambiguidade de ownership.
- Estados de `Sale`, `PaymentIntent`, `FraudAlert` e `ManualReviewCase` ainda nao cobrem toda a maquina de estados desejada.
- `notification_outbox` nao tinha `correlation_id`, reduzindo rastreabilidade operacional.
- `ledger_entries.source_event_id` era opcional no modelo, embora o criterio financeiro exija origem auditavel.
- O Agentic Reconciliation Agent emitia eventos, mas nao persistia `ReconciliationRecord`; dashboard/relatorios podiam ficar cegos para divergencias agentic.
- Timeout marcava `PaymentIntent` como timeout, mas nao bloqueava explicitamente a `Sale`.
- Divergencias e pagamentos orfaos geravam alertas, mas nem sempre colocavam sale/payment intent em estado de revisao.
- `manual_release_sale` gerava evento/fraud alert, mas nao criava caso formal de revisao manual.
- Observabilidade ainda e preparatoria: OpenTelemetry esta instrumentado, mas metricas de dominio ainda nao estao expostas em Prometheus.
- Testes ainda nao cobrem todos os fluxos criticos exigidos.

## 4. O que esta mal acoplado

- `developer_api.py` reutiliza diretamente funcoes de rota de `payments.py`, misturando camada HTTP publica com implementacao interna.
- Regras de reconciliacao existem em `services/reconciliation.py` e tambem dentro do LangGraph; isso pode divergir sem uma interface compartilhada.
- `payments.py` ainda concentra criacao de sale, payment intent, Pix charge e simulacao de webhook, enquanto o ideal seria separar use cases.
- O frontend usa endpoint de simulacao direta (`/payments/pix/webhooks/confirmation`) para demo; aceitavel para MVP, mas precisa ficar documentado como mock.
- Ha duplicacao estrutural entre `backend/` e `services/api`, e entre `frontend/` e `apps/web`.

## 5. O que precisa ser refatorado

- Centralizar regras de reconciliacao em um servico unico usado por API e agentes.
- Mover criacao de sale/payment intent/charge para use cases ou services de dominio, mantendo rotas finas.
- Criar camada de Application Services para os fluxos criticos: sale creation, pix charge creation, webhook ingestion, reconciliation finalization, timeout handling.
- Expandir e padronizar enums de estados.
- Padronizar eventos compensatorios para bloqueio, revisao manual, timeout e tentativa de liberacao manual.
- Tornar `source_event_id` obrigatorio em novas ledger entries.
- Remover ou documentar como legado as pastas `backend/` e `frontend/`.
- Separar clearly API interna do dashboard e API publica de terceiros.

## 6. Riscos tecnicos

- `Base.metadata.create_all()` em startup facilita demo, mas nao substitui Alembic em evolucao real de schema.
- A migracao `0001_initial.py` pode ficar divergente dos modelos atuais se nao for atualizada com as novas tabelas/colunas.
- O checkpointer Postgres do LangGraph usa a mesma `DATABASE_URL`; se a lib nao criar estrutura ou permissao faltar, cai para memory checkpointer.
- Fluxos agentic ainda rodam sincronos dentro da request HTTP; em producao, webhooks deveriam responder rapido e processar por fila.
- Concorrencia no hash chain pode causar cadeia inconsistente se eventos simultaneos do mesmo tenant forem gravados sem controle transacional/lock.
- Alguns textos/arquivos mostram encoding quebrado em portugues, indicando risco de charset misto no repo.

## 7. Riscos de seguranca

- `MASTER_API_KEY=changeme` e `JWT_SECRET_KEY=change_me_super_secret` aparecem como default para demo; producao exige secret forte via ambiente.
- Provider credentials ainda nao tem criptografia aplicada na pratica.
- Webhook replay protection ainda depende majoritariamente de `external_event_id`; falta janela temporal/timestamp por provider.
- CORS default configuravel existe, mas `allow_origins` permissivo em dev pode vazar em deploy se mal configurado.
- Logs estruturados ainda nao mascaram automaticamente payloads sensiveis.
- Nao ha politica formal de retencao/anonimizacao LGPD nos modelos.

## 8. Riscos de modelagem financeira

- `Sale.amount`, `PaymentIntent.amount`, `expected_amount`, `received_amount` usam `Numeric`, mas os fluxos operacionais misturam reais e centavos; centavos deveriam ser a fonte primaria.
- Ledger tinha `source_event_id` opcional; isso enfraquece a prova de origem.
- Nao existe conta contabil normalizada por tenant/provider; o MVP usa accounts fixas (`cash_in_transit`, `sales_revenue`).
- Reconciliacao agentic nao gravava `ReconciliationRecord`, impactando relatorios e auditoria de divergencia.
- `PixCharge.status=confirmed` pode mascarar estados intermediarios como payment_received/reconciling se usado cedo demais.
- Reembolsos, chargebacks e reversoes ainda sao estruturas preparadas, nao fluxos fechados.

## 9. Proximas acoes prioritarias

1. Expandir estados e eventos para refletir bloqueio, timeout, revisao manual e conciliacao.
2. Adicionar `correlation_id` em `notification_outbox` e exigir `source_event_id` para ledger entries novas.
3. Fazer o Agentic Reconciliation Agent persistir `ReconciliationRecord` e atualizar estados de sale/payment intent em divergencias.
4. Fazer Timeout Watchdog bloquear explicitamente a venda e abrir revisao manual.
5. Fazer tentativa manual de liberacao abrir manual review case.
6. Criar `docs/multi-cloud-architecture.md` e `docs/demo-flows.md`.
7. Atualizar README com disclaimers regulatorio e antifraude.
8. Adicionar testes dos fluxos criticos: Pix aprovado, valor divergente, duplicado, orfao, timeout, ledger, tenant isolation, hash chain.
9. Definir `services/api` e `apps/web` como arvores oficiais; marcar `backend/` e `frontend/` como legado ou remover em etapa controlada.
