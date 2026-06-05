from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import DBSession, MasterApiKeyDep
from app.db.models import (
    EventStore,
    FraudAlert,
    LedgerEntry,
    ManualReviewCase,
    NotificationOutbox,
    PaymentIntent,
    PaymentIntentStatus,
    PixCharge,
    ReconciliationRecord,
    Sale,
)
from app.schemas.events import EventStoreRead
from app.schemas.ledger import LedgerEntryRead
from app.schemas.pix import PixChargeCreate, PixChargeRead
from app.schemas.sale import SaleCreate, SaleRead
from app.api.routes.payments import create_sale, generate_pix_charge
from app.services.event_catalog import EventType
from app.services.ledger import append_event
from app.services.reporting import dashboard_metrics

router = APIRouter(tags=["developer-api"])


@router.post("/sales", response_model=SaleRead)
def create_sale_public(_: MasterApiKeyDep, payload: SaleCreate, db: DBSession) -> Sale:
    return create_sale(None, payload, db)  # type: ignore[arg-type]


@router.get("/sales", response_model=list[SaleRead])
def list_sales_public(
    _: MasterApiKeyDep,
    tenant_id: str,
    company_id: str,
    db: DBSession,
    limit: int = Query(default=100, le=500),
) -> list[Sale]:
    return db.scalars(
        select(Sale)
        .where(Sale.tenant_id == tenant_id, Sale.company_id == company_id)
        .order_by(Sale.opened_at.desc())
        .limit(limit)
    ).all()


@router.get("/sales/{id}", response_model=SaleRead)
def get_sale_public(_: MasterApiKeyDep, id: str, tenant_id: str, db: DBSession) -> Sale:
    sale = db.scalar(select(Sale).where(Sale.id == id, Sale.tenant_id == tenant_id))
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found.")
    return sale


@router.post("/payment-intents")
def create_payment_intent_public(_: MasterApiKeyDep, tenant_id: str, sale_id: str, db: DBSession) -> dict:
    payment_intent = db.scalar(
        select(PaymentIntent).where(PaymentIntent.tenant_id == tenant_id, PaymentIntent.sale_id == sale_id)
    )
    if not payment_intent:
        sale = db.scalar(select(Sale).where(Sale.id == sale_id, Sale.tenant_id == tenant_id))
        if not sale:
            return {"status": "sale_not_found"}
        payment_intent = PaymentIntent(
            tenant_id=tenant_id,
            sale_id=sale.id,
            method=sale.expected_method,
            provider="mock_pix",
            amount=sale.expected_amount_cents / 100,
            expected_amount=sale.expected_amount_cents / 100,
            status=PaymentIntentStatus.AWAITING_PAYMENT.value,
        )
        db.add(payment_intent)
        db.flush()
        append_event(
            db,
            tenant_id=tenant_id,
            aggregate_type="payment_intent",
            aggregate_id=payment_intent.id,
            event_type=EventType.PAYMENT_INTENT_CREATED.value,
            payload={"sale_id": sale.id, "provider": payment_intent.provider, "method": payment_intent.method},
            source="developer_api",
            correlation_id=sale.external_ref,
        )
        db.commit()
    return {
        "id": payment_intent.id,
        "status": payment_intent.status,
        "provider": payment_intent.provider,
        "method": payment_intent.method,
    }


@router.get("/payment-intents/{id}")
def get_payment_intent_public(_: MasterApiKeyDep, id: str, tenant_id: str, db: DBSession) -> dict:
    payment_intent = db.scalar(
        select(PaymentIntent).where(PaymentIntent.id == id, PaymentIntent.tenant_id == tenant_id)
    )
    if not payment_intent:
        raise HTTPException(status_code=404, detail="Payment intent not found.")
    return {
        "id": payment_intent.id,
        "tenant_id": payment_intent.tenant_id,
        "sale_id": payment_intent.sale_id,
        "method": payment_intent.method,
        "provider": payment_intent.provider,
        "status": payment_intent.status,
        "expected_amount": float(payment_intent.expected_amount),
        "received_amount": float(payment_intent.received_amount) if payment_intent.received_amount else None,
        "expires_at": payment_intent.expires_at,
        "paid_at": payment_intent.paid_at,
    }


@router.post("/pix/charges", response_model=PixChargeRead)
def create_pix_charge_public(_: MasterApiKeyDep, payload: PixChargeCreate, db: DBSession) -> PixCharge:
    return generate_pix_charge(None, payload, db)  # type: ignore[arg-type]


@router.get("/pix/charges/{id}", response_model=PixChargeRead)
def get_pix_charge_public(_: MasterApiKeyDep, id: str, tenant_id: str, db: DBSession) -> PixCharge:
    charge = db.scalar(select(PixCharge).where(PixCharge.id == id, PixCharge.tenant_id == tenant_id))
    if not charge:
        raise HTTPException(status_code=404, detail="Pix charge not found.")
    return charge


@router.get("/payments/{id}")
def get_payment_public(_: MasterApiKeyDep, id: str, tenant_id: str, db: DBSession) -> dict:
    payment_intent = db.scalar(select(PaymentIntent).where(PaymentIntent.id == id, PaymentIntent.tenant_id == tenant_id))
    if not payment_intent:
        return {"status": "not_found"}
    return {
        "id": payment_intent.id,
        "sale_id": payment_intent.sale_id,
        "status": payment_intent.status,
        "provider": payment_intent.provider,
        "amount": float(payment_intent.amount),
    }


@router.get("/events", response_model=list[EventStoreRead])
def list_events_public(_: MasterApiKeyDep, tenant_id: str, db: DBSession, limit: int = Query(default=100, le=500)) -> list[EventStore]:
    return db.scalars(
        select(EventStore).where(EventStore.tenant_id == tenant_id).order_by(EventStore.id.desc()).limit(limit)
    ).all()


@router.get("/ledger", response_model=list[LedgerEntryRead])
def list_ledger_public(_: MasterApiKeyDep, tenant_id: str, db: DBSession, limit: int = Query(default=100, le=500)) -> list[LedgerEntry]:
    return db.scalars(
        select(LedgerEntry).where(LedgerEntry.tenant_id == tenant_id).order_by(LedgerEntry.created_at.desc()).limit(limit)
    ).all()


@router.get("/reconciliation")
def list_reconciliation_public(
    _: MasterApiKeyDep, tenant_id: str, company_id: str, db: DBSession, limit: int = Query(default=100, le=500)
) -> list[ReconciliationRecord]:
    return db.scalars(
        select(ReconciliationRecord)
        .where(ReconciliationRecord.tenant_id == tenant_id, ReconciliationRecord.company_id == company_id)
        .order_by(ReconciliationRecord.created_at.desc())
        .limit(limit)
    ).all()


@router.get("/fraud-alerts")
def list_fraud_alerts_public(_: MasterApiKeyDep, tenant_id: str, db: DBSession, limit: int = Query(default=100, le=500)) -> list[FraudAlert]:
    return db.scalars(
        select(FraudAlert).where(FraudAlert.tenant_id == tenant_id).order_by(FraudAlert.created_at.desc()).limit(limit)
    ).all()


@router.get("/manual-review-cases")
def list_manual_review_cases_public(
    _: MasterApiKeyDep,
    tenant_id: str,
    db: DBSession,
    limit: int = Query(default=100, le=500),
) -> list[ManualReviewCase]:
    return db.scalars(
        select(ManualReviewCase)
        .where(ManualReviewCase.tenant_id == tenant_id)
        .order_by(ManualReviewCase.created_at.desc())
        .limit(limit)
    ).all()


@router.get("/notifications")
def list_notifications_public(
    _: MasterApiKeyDep,
    tenant_id: str,
    db: DBSession,
    limit: int = Query(default=100, le=500),
) -> list[NotificationOutbox]:
    return db.scalars(
        select(NotificationOutbox)
        .where(NotificationOutbox.tenant_id == tenant_id)
        .order_by(NotificationOutbox.created_at.desc())
        .limit(limit)
    ).all()


@router.get("/dashboard")
def get_dashboard_public(_: MasterApiKeyDep, tenant_id: str, company_id: str, db: DBSession) -> dict:
    from datetime import datetime, timezone

    return dashboard_metrics(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        business_date=datetime.now(timezone.utc).date(),
    )
