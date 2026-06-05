from datetime import date, timezone, datetime

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import ApiKeyDep, DBSession
from app.db.models import FraudFlag
from app.schemas.dashboard import AISummaryResponse, CashClosureSummary, DashboardMetrics
from app.schemas.reconciliation import FraudFlagRead, ReconciliationRecordRead
from app.services.ai_summary import generate_daily_ai_summary
from app.services.reporting import dashboard_metrics, generate_cash_closure, list_recent_divergences

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(
    _: ApiKeyDep,
    db: DBSession,
    company_id: str = Query(...),
    business_date: date | None = Query(default=None),
) -> dict:
    if not business_date:
        business_date = datetime.now(timezone.utc).date()
    return dashboard_metrics(db, company_id=company_id, business_date=business_date)


@router.get("/divergences", response_model=list[ReconciliationRecordRead])
def get_divergences(
    _: ApiKeyDep,
    db: DBSession,
    company_id: str = Query(...),
    limit: int = Query(default=30, ge=1, le=100),
) -> list:
    return list_recent_divergences(db, company_id=company_id, limit=limit)


@router.get("/fraud-flags", response_model=list[FraudFlagRead])
def get_fraud_flags(
    _: ApiKeyDep,
    db: DBSession,
    company_id: str = Query(...),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[FraudFlag]:
    return db.scalars(
        select(FraudFlag).where(FraudFlag.company_id == company_id).order_by(FraudFlag.created_at.desc()).limit(limit)
    ).all()


@router.get("/closeout", response_model=CashClosureSummary)
def get_closeout_report(
    _: ApiKeyDep,
    db: DBSession,
    company_id: str = Query(...),
    store_id: str = Query(...),
    business_date: date | None = Query(default=None),
) -> dict:
    if not business_date:
        business_date = datetime.now(timezone.utc).date()
    return generate_cash_closure(db, company_id=company_id, store_id=store_id, business_date=business_date)


@router.get("/ai-summary", response_model=AISummaryResponse)
def get_ai_summary(
    _: ApiKeyDep,
    db: DBSession,
    company_id: str = Query(...),
    store_id: str = Query(...),
    business_date: date | None = Query(default=None),
) -> dict:
    if not business_date:
        business_date = datetime.now(timezone.utc).date()
    metrics = dashboard_metrics(db, company_id=company_id, business_date=business_date)
    closure = generate_cash_closure(db, company_id=company_id, store_id=store_id, business_date=business_date)
    return generate_daily_ai_summary(
        company_id=company_id,
        business_date=business_date,
        metrics=metrics,
        closure=closure,
    )
