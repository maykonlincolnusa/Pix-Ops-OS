from sqlalchemy.orm import Session

from app.db.models import FraudAlert, FraudFlag, FraudSeverity


def create_fraud_flag(
    db: Session,
    *,
    tenant_id: str,
    company_id: str,
    store_id: str | None,
    sale_id: str | None,
    txid: str | None,
    severity: FraudSeverity,
    flag_type: str,
    description: str,
) -> FraudFlag:
    flag = FraudFlag(
        tenant_id=tenant_id,
        company_id=company_id,
        store_id=store_id,
        sale_id=sale_id,
        txid=txid,
        severity=severity.value,
        flag_type=flag_type,
        description=description,
    )
    db.add(flag)
    db.flush()
    return flag


def create_fraud_alert(
    db: Session,
    *,
    tenant_id: str,
    severity: FraudSeverity,
    category: str,
    reason: str,
    related_payment_id: str | None = None,
    related_sale_id: str | None = None,
    evidence: dict | None = None,
) -> FraudAlert:
    alert = FraudAlert(
        tenant_id=tenant_id,
        severity=severity.value,
        category=category,
        reason=reason,
        related_payment_id=related_payment_id,
        related_sale_id=related_sale_id,
        evidence=evidence or {},
    )
    db.add(alert)
    db.flush()
    return alert
