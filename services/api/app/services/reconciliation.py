from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PixCharge, PixChargeStatus, ReconciliationRecord, ReconciliationStatus, Sale, SaleStatus


def reconcile_sale(db: Session, sale: Sale) -> ReconciliationRecord:
    charge = db.scalar(select(PixCharge).where(PixCharge.sale_id == sale.id))
    expected = sale.expected_amount_cents

    if not charge or charge.status != PixChargeStatus.CONFIRMED.value:
        sale.status = SaleStatus.PENDING.value
        record = ReconciliationRecord(
            tenant_id=sale.tenant_id,
            company_id=sale.company_id,
            store_id=sale.store_id,
            sale_id=sale.id,
            txid=charge.txid if charge else None,
            expected_amount_cents=expected,
            received_amount_cents=charge.confirmed_amount_cents if charge else None,
            status=ReconciliationStatus.PENDING.value,
            reason="Venda aguardando confirmação real do provedor de pagamento.",
        )
        db.add(record)
        db.flush()
        return record

    received = charge.confirmed_amount_cents or 0
    if received == expected:
        sale.status = SaleStatus.PAID.value
        sale.paid_at = charge.confirmed_at or datetime.now(timezone.utc)
        status = ReconciliationStatus.MATCHED.value
        reason = "Txid e valor conferem com a venda esperada."
    elif received < expected:
        sale.status = SaleStatus.DIVERGENT.value
        status = ReconciliationStatus.UNDERPAID.value
        reason = "Pagamento confirmado com valor menor que o esperado."
    else:
        sale.status = SaleStatus.DIVERGENT.value
        status = ReconciliationStatus.OVERPAID.value
        reason = "Pagamento confirmado com valor maior que o esperado."

    record = ReconciliationRecord(
        tenant_id=sale.tenant_id,
        company_id=sale.company_id,
        store_id=sale.store_id,
        sale_id=sale.id,
        txid=charge.txid,
        expected_amount_cents=expected,
        received_amount_cents=received,
        status=status,
        reason=reason,
    )
    db.add(record)
    db.flush()
    return record


def reconcile_unexpected_payment(
    db: Session,
    *,
    tenant_id: str,
    company_id: str,
    txid: str,
    received_amount_cents: int,
) -> ReconciliationRecord:
    record = ReconciliationRecord(
        tenant_id=tenant_id,
        company_id=company_id,
        store_id=None,
        sale_id=None,
        txid=txid,
        expected_amount_cents=None,
        received_amount_cents=received_amount_cents,
        status=ReconciliationStatus.ORPHAN_PAYMENT.value,
        reason="Pagamento Pix recebido sem venda/cobrança correspondente.",
    )
    db.add(record)
    db.flush()
    return record
