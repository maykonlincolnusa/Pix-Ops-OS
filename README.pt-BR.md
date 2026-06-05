# PixOps OS

**Real-Time Payment Operations, Reconciliation & Anti-Fraud Platform**

PixOps OS e uma plataforma de operacoes financeiras em tempo real para empresas no Brasil, conectando Pix, bancos, maquininhas, PSPs e adquirentes em um ledger orientado a eventos para conciliacao, antifraude e inteligencia financeira.

## Por Que Empresas Internacionais Atuam no Brasil

Empresas internacionais atuam no Brasil porque o pais combina:

- mercado de pagamentos de grande escala,
- alta adocao de meios digitais, com Pix como trilho dominante,
- grande base de PMEs e empresas com dor real de conciliacao,
- ecossistema fragmentado entre bancos, PSPs, adquirentes e gateways.

Para empresas globais, o Brasil e estrategico: o volume e alto, a complexidade operacional e regulatoria e relevante, e existe demanda clara por plataformas que tragam controle financeiro em tempo real.

## Posicionamento do Produto

- Nao e banco e nao se apresenta como instituicao financeira.
- Opera como camada acima dos provedores financeiros.
- Nao promete bloquear 100% das fraudes.
- Reduz fraude operacional, comprovante falso, erro humano e divergencias de caixa.

## Escopo MVP

- onboarding multi-tenant (tenant, empresa, loja, operador e caixa),
- fluxo venda -> payment intent -> cobranca Pix -> webhook -> conciliacao,
- event store append-only com hash chain,
- ledger entries com abordagem double-entry basica,
- regras antifraude iniciais,
- dashboard operacional em tempo real,
- API para terceiros.

## Execucao Rapida

```bash
docker compose up --build
```

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Documentacao Tecnica

- [Arquitetura](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/architecture.md)
- [API](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/api.md)
- [Catalogo de Eventos](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/event-catalog.md)
- [Seguranca](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/security.md)
