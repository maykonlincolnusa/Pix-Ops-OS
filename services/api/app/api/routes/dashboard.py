from datetime import date, datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DBSession, MasterApiKeyDep
from app.db.models import EventStore, FraudAlert, LedgerEntry
from app.schemas.dashboard import AISummaryResponse, CashClosureSummary, DashboardMetrics
from app.schemas.events import EventStoreRead
from app.schemas.ledger import LedgerEntryRead
from app.schemas.reconciliation import ReconciliationRecordRead
from app.services.ai_summary import generate_daily_ai_summary
from app.services.event_catalog import EventType
from app.services.ledger import append_event
from app.services.reporting import dashboard_metrics, generate_cash_closure, list_recent_divergences

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    company_id: str = Query(...),
    business_date: date | None = Query(default=None),
) -> dict:
    if not business_date:
        business_date = datetime.now(timezone.utc).date()
    return dashboard_metrics(db, tenant_id=tenant_id, company_id=company_id, business_date=business_date)


@router.get("/events", response_model=list[EventStoreRead])
def get_event_timeline(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[EventStore]:
    return db.scalars(
        select(EventStore).where(EventStore.tenant_id == tenant_id).order_by(EventStore.id.desc()).limit(limit)
    ).all()


@router.get("/ledger", response_model=list[LedgerEntryRead])
def get_ledger(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[LedgerEntry]:
    return db.scalars(
        select(LedgerEntry).where(LedgerEntry.tenant_id == tenant_id).order_by(LedgerEntry.created_at.desc()).limit(limit)
    ).all()


@router.get("/divergences", response_model=list[ReconciliationRecordRead])
def get_divergences(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    company_id: str = Query(...),
    limit: int = Query(default=30, ge=1, le=100),
) -> list:
    return list_recent_divergences(db, tenant_id=tenant_id, company_id=company_id, limit=limit)


@router.get("/fraud-alerts")
def get_fraud_alerts(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    limit: int = Query(default=30, ge=1, le=200),
) -> list[FraudAlert]:
    return db.scalars(
        select(FraudAlert)
        .where(FraudAlert.tenant_id == tenant_id)
        .order_by(FraudAlert.created_at.desc())
        .limit(limit)
    ).all()


@router.get("/closeout", response_model=CashClosureSummary)
def get_closeout_report(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    company_id: str = Query(...),
    store_id: str = Query(...),
    business_date: date | None = Query(default=None),
) -> dict:
    if not business_date:
        business_date = datetime.now(timezone.utc).date()
    return generate_cash_closure(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        store_id=store_id,
        business_date=business_date,
    )


@router.get("/ai-summary", response_model=AISummaryResponse)
def get_ai_summary(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    company_id: str = Query(...),
    store_id: str = Query(...),
    business_date: date | None = Query(default=None),
) -> dict:
    if not business_date:
        business_date = datetime.now(timezone.utc).date()
    metrics = dashboard_metrics(db, tenant_id=tenant_id, company_id=company_id, business_date=business_date)
    closure = generate_cash_closure(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        store_id=store_id,
        business_date=business_date,
    )
    summary = generate_daily_ai_summary(
        company_id=company_id,
        business_date=business_date,
        metrics=metrics,
        closure=closure,
    )
    append_event(
        db,
        tenant_id=tenant_id,
        aggregate_type="ai",
        aggregate_id=store_id,
        event_type=EventType.AI_SUMMARY_GENERATED.value,
        payload={"business_date": business_date.isoformat(), "store_id": store_id},
        source="ai_copilot",
    )
    db.commit()
    return summary


@router.post("/ai-query")
def ai_query(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    company_id: str = Query(...),
    question: str = Query(..., min_length=2),
) -> dict:
    question_l = question.lower()
    if "pendente" in question_l:
        answer = "Use /dashboard/divergences para revisar pagamentos pendentes e divergentes."
    elif "recebi hoje" in question_l or "recebido" in question_l:
        today = datetime.now(timezone.utc).date()
        metrics = dashboard_metrics(db, tenant_id=tenant_id, company_id=company_id, business_date=today)
        answer = f"Recebido confirmado hoje: R$ {metrics['received_total_cents'] / 100:.2f}."
    else:
        answer = "Consulta disponível no MVP via regras. Em produção, conecte com RAG interno."

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
