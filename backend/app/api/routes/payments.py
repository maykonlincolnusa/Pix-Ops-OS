from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import ApiKeyDep, DBSession
from app.db.models import (
    CashRegister,
    Company,
    FraudSeverity,
    Operator,
    PixCharge,
    PixChargeStatus,
    ReconciliationStatus,
    Sale,
    Store,
)
from app.schemas.pix import PixChargeCreate, PixChargeRead, PixWebhookPayload, PixWebhookResult
from app.schemas.sale import SaleCreate, SaleRead
from app.services.fraud import create_fraud_flag
from app.services.ledger import append_ledger_event
from app.services.pix import create_pix_charge
from app.services.reconciliation import reconcile_sale, reconcile_unexpected_payment

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/sales", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(_: ApiKeyDep, payload: SaleCreate, db: DBSession) -> Sale:
    company = db.scalar(select(Company).where(Company.id == payload.company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    store = db.scalar(select(Store).where(Store.id == payload.store_id, Store.company_id == payload.company_id))
    if not store:
        raise HTTPException(status_code=404, detail="Store not found for this company.")

    if payload.operator_id:
        operator = db.scalar(
            select(Operator).where(Operator.id == payload.operator_id, Operator.company_id == payload.company_id)
        )
        if not operator:
            raise HTTPException(status_code=404, detail="Operator not found for this company.")

    if payload.cash_register_id:
        cash = db.scalar(
            select(CashRegister).where(
                CashRegister.id == payload.cash_register_id,
                CashRegister.company_id == payload.company_id,
            )
        )
        if not cash:
            raise HTTPException(status_code=404, detail="Cash register not found for this company.")

    sale = Sale(
        company_id=payload.company_id,
        store_id=payload.store_id,
        cash_register_id=payload.cash_register_id,
        operator_id=payload.operator_id,
        external_ref=payload.external_ref,
        description=payload.description,
        expected_amount_cents=payload.expected_amount_cents,
        expected_method=payload.expected_method,
    )
    db.add(sale)
    try:
        db.flush()
        append_ledger_event(
            db,
            company_id=sale.company_id,
            store_id=sale.store_id,
            sale_id=sale.id,
            source="POS",
            event_type="SALE_EXPECTED_CREATED",
            reference_id=sale.external_ref,
            amount_cents=sale.expected_amount_cents,
            payload={
                "cash_register_id": sale.cash_register_id,
                "operator_id": sale.operator_id,
                "expected_method": sale.expected_method,
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Sale external reference already exists.") from exc
    return sale


@router.get("/sales", response_model=list[SaleRead])
def list_sales(
    _: ApiKeyDep,
    db: DBSession,
    company_id: str = Query(...),
    business_date: date | None = Query(default=None),
) -> list[Sale]:
    query = select(Sale).where(Sale.company_id == company_id)
    if business_date:
        start = datetime.combine(business_date, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        query = query.where(Sale.opened_at >= start, Sale.opened_at < end)
    return db.scalars(query.order_by(Sale.opened_at.desc()).limit(200)).all()


@router.post("/pix/charges", response_model=PixChargeRead, status_code=status.HTTP_201_CREATED)
def generate_pix_charge(_: ApiKeyDep, payload: PixChargeCreate, db: DBSession) -> PixCharge:
    try:
        charge = create_pix_charge(db, payload)
        append_ledger_event(
            db,
            company_id=charge.company_id,
            store_id=charge.sale.store_id,
            sale_id=charge.sale_id,
            source="PAYMENT_GATEWAY",
            event_type="PIX_CHARGE_CREATED",
            reference_id=charge.txid,
            amount_cents=charge.amount_cents,
            payload={"pix_key": charge.pix_key, "expires_at": charge.expires_at.isoformat()},
        )
        db.commit()
        return charge
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pix/webhooks/confirmation", response_model=PixWebhookResult)
def confirm_pix_webhook(_: ApiKeyDep, payload: PixWebhookPayload, db: DBSession) -> PixWebhookResult:
    charge = db.scalar(select(PixCharge).where(PixCharge.txid == payload.txid))

    if not charge:
        if not payload.company_id:
            raise HTTPException(
                status_code=404,
                detail="Unknown txid and company_id missing. Include company_id for unexpected payment tracking.",
            )

        reconciliation = reconcile_unexpected_payment(
            db,
            company_id=payload.company_id,
            txid=payload.txid,
            received_amount_cents=payload.amount_cents,
        )
        flag = create_fraud_flag(
            db,
            company_id=payload.company_id,
            store_id=None,
            sale_id=None,
            txid=payload.txid,
            severity=FraudSeverity.HIGH,
            flag_type="UNEXPECTED_PIX_CONFIRMATION",
            description="Webhook Pix recebido para txid inexistente no sistema.",
        )
        append_ledger_event(
            db,
            company_id=payload.company_id,
            store_id=None,
            sale_id=None,
            source="PIX_WEBHOOK",
            event_type="PIX_PAYMENT_UNEXPECTED",
            reference_id=payload.txid,
            amount_cents=payload.amount_cents,
            payload={"end_to_end_id": payload.end_to_end_id, "raw_payload": payload.raw_payload},
        )
        db.commit()
        return PixWebhookResult(
            txid=payload.txid,
            sale_id=None,
            status="UNEXPECTED_PAYMENT",
            reconciliation_status=reconciliation.status,
            fraud_flag_id=flag.id,
        )

    sale = db.scalar(select(Sale).where(Sale.id == charge.sale_id))
    if not sale:
        db.rollback()
        raise HTTPException(status_code=500, detail="Sale linked to txid not found.")

    fraud_flag_id: str | None = None
    paid_at = payload.paid_at or datetime.now(timezone.utc)

    if charge.status == PixChargeStatus.CONFIRMED.value:
        if charge.end_to_end_id != payload.end_to_end_id or charge.confirmed_amount_cents != payload.amount_cents:
            flag = create_fraud_flag(
                db,
                company_id=charge.company_id,
                store_id=sale.store_id,
                sale_id=sale.id,
                txid=charge.txid,
                severity=FraudSeverity.HIGH,
                flag_type="DUPLICATE_CONFIRMATION",
                description="Cobrança Pix já confirmada recebeu nova confirmação com dados divergentes.",
            )
            fraud_flag_id = flag.id
        append_ledger_event(
            db,
            company_id=charge.company_id,
            store_id=sale.store_id,
            sale_id=sale.id,
            source="PIX_WEBHOOK",
            event_type="PIX_WEBHOOK_REPLAY",
            reference_id=charge.txid,
            amount_cents=payload.amount_cents,
            payload={"end_to_end_id": payload.end_to_end_id},
        )
        reconciliation = reconcile_sale(db, sale)
        db.commit()
        return PixWebhookResult(
            txid=charge.txid,
            sale_id=sale.id,
            status="ALREADY_CONFIRMED",
            reconciliation_status=reconciliation.status,
            fraud_flag_id=fraud_flag_id,
        )

    charge.status = PixChargeStatus.CONFIRMED.value
    charge.confirmed_at = paid_at
    charge.confirmed_amount_cents = payload.amount_cents
    charge.end_to_end_id = payload.end_to_end_id

    append_ledger_event(
        db,
        company_id=charge.company_id,
        store_id=sale.store_id,
        sale_id=sale.id,
        source="PIX_WEBHOOK",
        event_type="PIX_PAYMENT_CONFIRMED",
        reference_id=charge.txid,
        amount_cents=payload.amount_cents,
        occurred_at=paid_at,
        payload={"end_to_end_id": payload.end_to_end_id, "raw_payload": payload.raw_payload},
    )

    reconciliation = reconcile_sale(db, sale)
    append_ledger_event(
        db,
        company_id=charge.company_id,
        store_id=sale.store_id,
        sale_id=sale.id,
        source="RECON_ENGINE",
        event_type="RECONCILIATION_COMPLETED",
        reference_id=charge.txid,
        amount_cents=payload.amount_cents,
        payload={"status": reconciliation.status, "reason": reconciliation.reason},
    )

    if reconciliation.status == ReconciliationStatus.AMOUNT_MISMATCH.value:
        flag = create_fraud_flag(
            db,
            company_id=charge.company_id,
            store_id=sale.store_id,
            sale_id=sale.id,
            txid=charge.txid,
            severity=FraudSeverity.MEDIUM,
            flag_type="AMOUNT_MISMATCH",
            description="Valor confirmado pelo webhook difere da venda registrada no caixa.",
        )
        fraud_flag_id = flag.id

    if paid_at > charge.expires_at:
        flag = create_fraud_flag(
            db,
            company_id=charge.company_id,
            store_id=sale.store_id,
            sale_id=sale.id,
            txid=charge.txid,
            severity=FraudSeverity.LOW,
            flag_type="LATE_CONFIRMATION",
            description="Confirmação de pagamento recebida após expiração da cobrança.",
        )
        fraud_flag_id = flag.id

    db.commit()
    return PixWebhookResult(
        txid=charge.txid,
        sale_id=sale.id,
        status=charge.status,
        reconciliation_status=reconciliation.status,
        fraud_flag_id=fraud_flag_id,
    )
