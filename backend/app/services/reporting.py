from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    CashClosureReport,
    FraudFlag,
    FraudStatus,
    LedgerEvent,
    PixCharge,
    PixChargeStatus,
    ReconciliationRecord,
    ReconciliationStatus,
    Sale,
    SaleStatus,
)


def day_bounds(business_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(business_date, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def to_int(value: int | None) -> int:
    return 0 if value is None else int(value)


def dashboard_metrics(db: Session, *, company_id: str, business_date: date) -> dict[str, Any]:
    start, end = day_bounds(business_date)

    total_sales = db.scalar(
        select(func.count(Sale.id)).where(
            Sale.company_id == company_id,
            Sale.opened_at >= start,
            Sale.opened_at < end,
        )
    ) or 0

    paid_sales = db.scalar(
        select(func.count(Sale.id)).where(
            Sale.company_id == company_id,
            Sale.opened_at >= start,
            Sale.opened_at < end,
            Sale.status == SaleStatus.PAID.value,
        )
    ) or 0

    pending_sales = db.scalar(
        select(func.count(Sale.id)).where(
            Sale.company_id == company_id,
            Sale.opened_at >= start,
            Sale.opened_at < end,
            Sale.status == SaleStatus.PENDING.value,
        )
    ) or 0

    divergent_sales = db.scalar(
        select(func.count(Sale.id)).where(
            Sale.company_id == company_id,
            Sale.opened_at >= start,
            Sale.opened_at < end,
            Sale.status == SaleStatus.DIVERGENT.value,
        )
    ) or 0

    expected_total = db.scalar(
        select(func.sum(Sale.expected_amount_cents)).where(
            Sale.company_id == company_id,
            Sale.opened_at >= start,
            Sale.opened_at < end,
        )
    )

    received_total = db.scalar(
        select(func.sum(PixCharge.confirmed_amount_cents)).where(
            PixCharge.company_id == company_id,
            PixCharge.status == PixChargeStatus.CONFIRMED.value,
            PixCharge.confirmed_at >= start,
            PixCharge.confirmed_at < end,
        )
    )

    open_fraud_flags = db.scalar(
        select(func.count(FraudFlag.id)).where(
            FraudFlag.company_id == company_id,
            FraudFlag.status == FraudStatus.OPEN.value,
        )
    ) or 0

    events = db.scalars(
        select(LedgerEvent)
        .where(LedgerEvent.company_id == company_id)
        .order_by(desc(LedgerEvent.sequence_no))
        .limit(10)
    ).all()

    latest_events = [
        {
            "event_id": event.event_id,
            "sequence_no": event.sequence_no,
            "source": event.source,
            "event_type": event.event_type,
            "reference_id": event.reference_id,
            "amount_cents": event.amount_cents,
            "occurred_at": event.occurred_at,
            "event_hash": event.event_hash,
        }
        for event in events
    ]

    return {
        "company_id": company_id,
        "business_date": business_date,
        "total_sales": total_sales,
        "paid_sales": paid_sales,
        "pending_sales": pending_sales,
        "divergent_sales": divergent_sales,
        "expected_total_cents": to_int(expected_total),
        "received_total_cents": to_int(received_total),
        "open_fraud_flags": open_fraud_flags,
        "latest_events": latest_events,
    }


def list_recent_divergences(db: Session, *, company_id: str, limit: int = 30) -> list[ReconciliationRecord]:
    return db.scalars(
        select(ReconciliationRecord)
        .where(
            ReconciliationRecord.company_id == company_id,
            or_(
                ReconciliationRecord.status == ReconciliationStatus.AMOUNT_MISMATCH.value,
                ReconciliationRecord.status == ReconciliationStatus.UNEXPECTED_PAYMENT.value,
                ReconciliationRecord.status == ReconciliationStatus.MISSING_PAYMENT.value,
            ),
        )
        .order_by(desc(ReconciliationRecord.created_at))
        .limit(limit)
    ).all()


def generate_cash_closure(
    db: Session, *, company_id: str, store_id: str, business_date: date
) -> dict[str, Any]:
    start, end = day_bounds(business_date)

    sales = db.scalars(
        select(Sale).where(
            Sale.company_id == company_id,
            Sale.store_id == store_id,
            Sale.opened_at >= start,
            Sale.opened_at < end,
        )
    ).all()

    expected_total = sum(s.expected_amount_cents for s in sales)
    paid_sales = [s for s in sales if s.status == SaleStatus.PAID.value]
    divergent_sales = [s for s in sales if s.status == SaleStatus.DIVERGENT.value]

    charges = db.scalars(
        select(PixCharge).where(
            PixCharge.company_id == company_id,
            PixCharge.confirmed_at >= start,
            PixCharge.confirmed_at < end,
        )
    ).all()
    received_total = sum(c.confirmed_amount_cents or 0 for c in charges)

    divergences = db.scalars(
        select(ReconciliationRecord).where(
            ReconciliationRecord.company_id == company_id,
            ReconciliationRecord.store_id == store_id,
            ReconciliationRecord.created_at >= start,
            ReconciliationRecord.created_at < end,
            ReconciliationRecord.status != ReconciliationStatus.MATCHED.value,
        )
    ).all()

    recommendations: list[str] = []
    if divergences:
        recommendations.append("Priorizar revisão manual dos txids com divergência antes do fechamento.")
    if len(divergent_sales) > 0:
        recommendations.append("Bloquear baixa manual de vendas divergentes sem confirmação do PSP.")
    if len(divergences) == 0:
        recommendations.append("Operação consistente: manter rotina de dupla checagem no encerramento.")

    summary = {
        "company_id": company_id,
        "store_id": store_id,
        "business_date": business_date,
        "totals": {
            "sales_count": len(sales),
            "paid_sales_count": len(paid_sales),
            "divergent_sales_count": len(divergent_sales),
            "expected_total_cents": expected_total,
            "received_total_cents": received_total,
            "difference_cents": received_total - expected_total,
        },
        "divergences": [
            {
                "sale_id": d.sale_id,
                "txid": d.txid,
                "status": d.status,
                "reason": d.reason,
                "expected_amount_cents": d.expected_amount_cents,
                "received_amount_cents": d.received_amount_cents,
                "created_at": d.created_at,
            }
            for d in divergences
        ],
        "recommendations": recommendations,
    }

    report = db.scalar(
        select(CashClosureReport).where(
            CashClosureReport.company_id == company_id,
            CashClosureReport.store_id == store_id,
            CashClosureReport.business_date == business_date,
        )
    )
    if report:
        report.summary = summary
    else:
        report = CashClosureReport(
            company_id=company_id,
            store_id=store_id,
            business_date=business_date,
            summary=summary,
        )
        db.add(report)
    db.flush()
    return summary
