from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.api.deps import DBSession, MasterApiKeyDep
from app.services.ai_summary import generate_daily_ai_summary
from app.services.event_catalog import EventType
from app.services.ledger import append_event
from app.services.reporting import dashboard_metrics, generate_cash_closure

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/daily-summary")
def daily_summary(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    company_id: str = Query(...),
    store_id: str = Query(...),
) -> dict:
    today = datetime.now(timezone.utc).date()
    metrics = dashboard_metrics(db, tenant_id=tenant_id, company_id=company_id, business_date=today)
    closure = generate_cash_closure(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        store_id=store_id,
        business_date=today,
    )
    summary = generate_daily_ai_summary(
        company_id=company_id,
        business_date=today,
        metrics=metrics,
        closure=closure,
    )
    append_event(
        db,
        tenant_id=tenant_id,
        aggregate_type="ai",
        aggregate_id=company_id,
        event_type=EventType.AI_SUMMARY_GENERATED.value,
        payload={"store_id": store_id, "business_date": today.isoformat()},
        source="ai_copilot",
    )
    db.commit()
    return summary


@router.post("/query")
def query_ai(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    company_id: str = Query(...),
    question: str = Query(..., min_length=2),
) -> dict:
    q = question.lower()
    today = datetime.now(timezone.utc).date()
    metrics = dashboard_metrics(db, tenant_id=tenant_id, company_id=company_id, business_date=today)
    if "quanto recebi" in q:
        answer = f"Você recebeu {metrics['received_total_cents'] / 100:.2f} BRL hoje."
    elif "pendentes" in q:
        answer = f"Há {metrics['pending_sales']} vendas pendentes no dia."
    elif "diverg" in q:
        answer = f"Há {metrics['divergent_sales']} vendas divergentes no dia."
    elif "suspeito" in q:
        answer = f"Existem {metrics['open_fraud_flags']} alertas de risco abertos."
    else:
        answer = "Pergunta registrada. No MVP as respostas usam SQL + regras, sem geração criativa."
    append_event(
        db,
        tenant_id=tenant_id,
        aggregate_type="ai",
        aggregate_id=company_id,
        event_type=EventType.AI_QUERY_EXECUTED.value,
        payload={"question": question, "answer": answer},
        source="ai_copilot",
    )
    db.commit()
    return {"question": question, "answer": answer}
