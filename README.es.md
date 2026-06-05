# PixOps OS

**Real-Time Payment Operations, Reconciliation & Anti-Fraud Platform**

PixOps OS es una plataforma de operaciones de pago en tiempo real para empresas en Brasil, conectando Pix, bancos, terminales de tarjeta, PSPs y adquirentes en un ledger unificado orientado a eventos para conciliacion, antifraude e inteligencia financiera.

## Por Que Empresas Internacionales Operan en Brasil

Las empresas internacionales operan en Brasil porque el pais ofrece:

- uno de los mayores volumenes de pagos del mundo,
- alta adopcion digital impulsada por Pix,
- gran demanda de PYMEs y empresas por conciliacion y control,
- ecosistema fragmentado de bancos, PSPs, adquirentes y gateways.

Para companias globales, Brasil es estrategico por su escala, complejidad operativa y necesidad real de visibilidad financiera en tiempo real.

## Posicionamiento del Producto

- No es banco ni reemplazo de institucion financiera.
- Capa operativa por encima de bancos y proveedores de pago.
- No promete prevenir el 100% del fraude.
- Reduce fraude operacional, comprobantes falsos, error humano y brechas de conciliacion.

## Alcance MVP

- onboarding multi-tenant (tenant, empresa, tienda, operador y caja),
- flujo venta -> payment intent -> cobro Pix -> webhook -> conciliacion,
- event store append-only con hash chain,
- ledger con enfoque double-entry basico,
- motor inicial de reglas antifraude,
- dashboard operativo en tiempo real,
- API para terceros.

## Inicio Rapido

```bash
docker compose up --build
```

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Documentacion Tecnica

- [Arquitectura](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/architecture.md)
- [API](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/api.md)
- [Catalogo de Eventos](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/event-catalog.md)
- [Seguridad](C:/Users/gomes/OneDrive/Área%20de%20Trabalho/PixOps%20OS/docs/security.md)
