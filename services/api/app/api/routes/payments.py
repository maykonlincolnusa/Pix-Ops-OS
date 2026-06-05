from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.agentic.router import run_agent_router
from app.agentic.store import create_manual_review_case
from app.api.deps import DBSession, MasterApiKeyDep
from app.core.security import require_roles
from app.db.models import (
    CashRegister,
    Company,
    FraudSeverity,
    Operator,
    PaymentIntent,
    PaymentIntentStatus,
    PixCharge,
    PixChargeStatus,
    ReconciliationStatus,
    Sale,
    SaleStatus,
    Store,
    User,
    UserRole,
)
from app.schemas.pix import PixChargeCreate, PixChargeRead, PixWebhookPayload, PixWebhookResult
from app.schemas.sale import SaleCreate, SaleRead
from app.services.event_catalog import EventType
from app.services.fraud import create_fraud_alert
from app.services.ledger import append_event
from app.services.pix import create_pix_charge

router = APIRouter(prefix="/payments", tags=["payments"])


class ManualReleasePayload(BaseModel):
    justification: str = Field(min_length=5, max_length=300)


@router.post("/sales", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(_: MasterApiKeyDep, payload: SaleCreate, db: DBSession) -> Sale:
    company = db.scalar(
        select(Company).where(Company.id == payload.company_id, Company.tenant_id == payload.tenant_id)
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    store = db.scalar(
        select(Store).where(
            Store.id == payload.store_id,
            Store.company_id == payload.company_id,
            Store.tenant_id == payload.tenant_id,
        )
    )
    if not store:
        raise HTTPException(status_code=404, detail="Store not found for this tenant.")

    if payload.operator_id:
        operator = db.scalar(
            select(Operator).where(
                Operator.id == payload.operator_id,
                Operator.company_id == payload.company_id,
                Operator.tenant_id == payload.tenant_id,
            )
        )
        if not operator:
            raise HTTPException(status_code=404, detail="Operator not found for this tenant.")

    if payload.cash_register_id:
        cash = db.scalar(
            select(CashRegister).where(
                CashRegister.id == payload.cash_register_id,
                CashRegister.company_id == payload.company_id,
                CashRegister.tenant_id == payload.tenant_id,
            )
        )
        if not cash:
            raise HTTPException(status_code=404, detail="Cash register not found for this tenant.")

    sale = Sale(
        tenant_id=payload.tenant_id,
        company_id=payload.company_id,
        store_id=payload.store_id,
        cash_register_id=payload.cash_register_id,
        operator_id=payload.operator_id,
        external_ref=payload.external_ref,
        description=payload.description,
        expected_amount_cents=payload.expected_amount_cents,
        amount=payload.expected_amount_cents / 100,
        expected_method=payload.expected_method.lower(),
        status=SaleStatus.AWAITING_PAYMENT.value,
    )
    db.add(sale)
    try:
        db.flush()
        payment_intent = PaymentIntent(
            tenant_id=sale.tenant_id,
            sale_id=sale.id,
            method=sale.expected_method,
            provider="mock_pix" if sale.expected_method == "pix" else "mock_card",
            amount=sale.expected_amount_cents / 100,
            expected_amount=sale.expected_amount_cents / 100,
            status=PaymentIntentStatus.AWAITING_PAYMENT.value,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
            metadata={"external_ref": sale.external_ref},
        )
        db.add(payment_intent)
        db.flush()

        append_event(
            db,
            tenant_id=sale.tenant_id,
            aggregate_type="sale",
            aggregate_id=sale.id,
            event_type=EventType.SALE_CREATED.value,
            payload={
                "sale_id": sale.id,
                "store_id": sale.store_id,
                "amount_cents": sale.expected_amount_cents,
                "method": sale.expected_method,
            },
            source="pos",
            correlation_id=sale.external_ref,
        )
        append_event(
            db,
            tenant_id=sale.tenant_id,
            aggregate_type="payment_intent",
            aggregate_id=payment_intent.id,
            event_type=EventType.PAYMENT_INTENT_CREATED.value,
            payload={
                "sale_id": sale.id,
                "payment_intent_id": payment_intent.id,
                "amount_cents": sale.expected_amount_cents,
                "provider": payment_intent.provider,
            },
            source="payment_engine",
            correlation_id=sale.external_ref,
        )
        append_event(
            db,
            tenant_id=sale.tenant_id,
            aggregate_type="payment_intent",
            aggregate_id=payment_intent.id,
            event_type=EventType.PAYMENT_INTENT_AWAITING_PAYMENT.value,
            payload={
                "payment_intent_id": payment_intent.id,
                "sale_id": sale.id,
                "expires_at": payment_intent.expires_at.isoformat() if payment_intent.expires_at else None,
            },
            source="payment_engine",
            correlation_id=sale.external_ref,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Sale external reference already exists.") from exc
    return sale


@router.get("/sales", response_model=list[SaleRead])
def list_sales(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    company_id: str = Query(...),
    business_date: date | None = Query(default=None),
) -> list[Sale]:
    query = select(Sale).where(Sale.tenant_id == tenant_id, Sale.company_id == company_id)
    if business_date:
        start = datetime.combine(business_date, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        query = query.where(Sale.opened_at >= start, Sale.opened_at < end)
    return db.scalars(query.order_by(Sale.opened_at.desc()).limit(200)).all()


@router.post("/pix/charges", response_model=PixChargeRead, status_code=status.HTTP_201_CREATED)
def generate_pix_charge(_: MasterApiKeyDep, payload: PixChargeCreate, db: DBSession) -> PixCharge:
    try:
        charge, payment_intent = create_pix_charge(db, payload, provider_name="mock_pix")
        append_event(
            db,
            tenant_id=payload.tenant_id,
            aggregate_type="pix_charge",
            aggregate_id=charge.id,
            event_type=EventType.PIX_CHARGE_CREATE_REQUESTED.value,
            payload={"sale_id": payload.sale_id, "amount_cents": charge.amount_cents},
            source="payment_engine",
            provider="mock_pix",
        )
        append_event(
            db,
            tenant_id=payload.tenant_id,
            aggregate_type="pix_charge",
            aggregate_id=charge.id,
            event_type=EventType.PIX_CHARGE_CREATED.value,
            payload={
                "txid": charge.txid,
                "location_id": charge.location_id,
                "amount_cents": charge.amount_cents,
                "payment_intent_id": payment_intent.id,
            },
            source="provider",
            provider="mock_pix",
        )
        run_agent_router(
            db,
            tenant_id=payload.tenant_id,
            event_type=EventType.PAYMENT_AWAITING_CONFIRMATION.value,
            aggregate_type="payment_intent",
            aggregate_id=payment_intent.id,
            payload={
                "payment_intent_id": payment_intent.id,
                "sale_id": payload.sale_id,
                "txid": charge.txid,
                "due_at": charge.expires_at.isoformat(),
            },
            metadata={
                "environment": "mvp",
                "provider": "mock_pix",
                "sale_id": payload.sale_id,
                "payment_intent_id": payment_intent.id,
            },
            correlation_id=payment_intent.id,
            causation_id=None,
            provider="mock_pix",
        )
        db.commit()
        return charge
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pix/charges/{charge_id}", response_model=PixChargeRead)
def get_pix_charge(_: MasterApiKeyDep, charge_id: str, tenant_id: str, db: DBSession) -> PixCharge:
    charge = db.scalar(select(PixCharge).where(PixCharge.id == charge_id, PixCharge.tenant_id == tenant_id))
    if not charge:
        raise HTTPException(status_code=404, detail="Pix charge not found.")
    return charge


@router.post("/pix/webhooks/confirmation", response_model=PixWebhookResult)
def confirm_pix_webhook(_: MasterApiKeyDep, payload: PixWebhookPayload, db: DBSession) -> PixWebhookResult:
    if not payload.tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required.")

    paid_at = payload.paid_at or datetime.now(timezone.utc)
    existing_charge = db.scalar(
        select(PixCharge).where(
            PixCharge.txid == payload.txid,
            PixCharge.tenant_id == payload.tenant_id,
        )
    )
    duplicate = existing_charge is not None and existing_charge.status == PixChargeStatus.CONFIRMED.value
    final_state = run_agent_router(
        db,
        tenant_id=payload.tenant_id,
        event_type=EventType.WEBHOOK_RECEIVED.value,
        aggregate_type="webhook",
        aggregate_id=payload.end_to_end_id,
        payload={
            "txid": payload.txid,
            "end_to_end_id": payload.end_to_end_id,
            "external_event_id": payload.end_to_end_id,
            "amount_cents": payload.amount_cents,
            "paid_at": paid_at.isoformat(),
            "company_id": payload.company_id,
            "signature_valid": True,
            "duplicate": duplicate,
            "status": "confirmed",
            "raw_payload": payload.raw_payload,
        },
        metadata={
            "tenant_id": payload.tenant_id,
            "provider": "mock_pix",
            "channel": "pix",
            "environment": "mvp",
            "sale_id": None,
            "payment_intent_id": None,
        },
        correlation_id=payload.txid,
        causation_id=payload.end_to_end_id,
        trace_id=None,
        provider="mock_pix",
        source_event_id=payload.end_to_end_id,
    )

    charge = existing_charge or db.scalar(
        select(PixCharge).where(
            PixCharge.txid == payload.txid,
            PixCharge.tenant_id == payload.tenant_id,
        )
    )
    sale_id = charge.sale_id if charge else None
    status_value = charge.status if charge else "orphan_payment"
    if final_state.get("reconciliation_status") == ReconciliationStatus.DUPLICATE.value:
        status_value = "duplicate_event_ignored"
    elif final_state.get("reconciliation_status") in {
        ReconciliationStatus.UNDERPAID.value,
        ReconciliationStatus.OVERPAID.value,
        ReconciliationStatus.ORPHAN_PAYMENT.value,
        "late_payment",
    }:
        status_value = "suspicious"

    db.commit()
    return PixWebhookResult(
        txid=payload.txid,
        sale_id=sale_id,
        status=status_value,
        reconciliation_status=final_state.get("reconciliation_status"),
        fraud_flag_id=None,
    )


@router.post("/sales/{sale_id}/manual-release")
def manual_release_sale(
    sale_id: str,
    payload: ManualReleasePayload,
    db: DBSession,
    user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.AUDITOR)),
) -> dict:
    sale = db.scalar(select(Sale).where(Sale.id == sale_id, Sale.tenant_id == user.tenant_id))
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found.")
    if sale.status == SaleStatus.PAID.value:
        return {"status": "already_paid", "sale_id": sale.id}

    sale.status = SaleStatus.MANUAL_REVIEW_REQUIRED.value
    db.add(sale)
    append_event(
        db,
        tenant_id=user.tenant_id,
        aggregate_type="sale",
        aggregate_id=sale.id,
        event_type=EventType.SALE_MANUAL_RELEASE_ATTEMPTED.value,
        payload={"justification": payload.justification, "actor_id": user.id},
        source="manual_operation",
        actor_type="user",
        actor_id=user.id,
    )
    append_event(
        db,
        tenant_id=user.tenant_id,
        aggregate_type="sale",
        aggregate_id=sale.id,
        event_type=EventType.SALE_RELEASE_BLOCKED.value,
        payload={"reason": "manual_release_without_financial_confirmation", "actor_id": user.id},
        source="manual_operation",
        actor_type="user",
        actor_id=user.id,
    )
    alert = create_fraud_alert(
        db,
        tenant_id=user.tenant_id,
        severity=FraudSeverity.HIGH,
        category="manual_confirmation_risk",
        reason="Tentativa de liberação manual sem confirmação financeira.",
        related_sale_id=sale.id,
        evidence={"justification": payload.justification, "user_id": user.id},
    )
    append_event(
        db,
        tenant_id=user.tenant_id,
        aggregate_type="fraud_alert",
        aggregate_id=alert.id,
        event_type=EventType.FRAUD_ALERT_CREATED.value,
        payload={
            "fraud_alert_id": alert.id,
            "category": alert.category,
            "severity": alert.severity,
            "reason": alert.reason,
        },
        source="manual_operation",
        actor_type="user",
        actor_id=user.id,
    )
    case = create_manual_review_case(
        db,
        tenant_id=user.tenant_id,
        sale_id=sale.id,
        payment_intent_id=sale.payment_intent.id if sale.payment_intent else None,
        fraud_alert_id=alert.id,
        severity=FraudSeverity.HIGH.value,
        summary="Tentativa de liberacao manual sem evento financeiro confirmado.",
        recommendation="Manter a venda bloqueada ate revisar timeline, webhook e ledger.",
    )
    append_event(
        db,
        tenant_id=user.tenant_id,
        aggregate_type="manual_review_case",
        aggregate_id=case.id,
        event_type=EventType.MANUAL_REVIEW_REQUIRED.value,
        payload={"manual_review_case_id": case.id, "sale_id": sale.id, "fraud_alert_id": alert.id},
        source="manual_operation",
        actor_type="user",
        actor_id=user.id,
    )
    db.commit()
    return {"status": "manual_review_required", "sale_id": sale.id, "manual_review_case_id": case.id}

