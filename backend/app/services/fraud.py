from sqlalchemy.orm import Session

from app.db.models import FraudFlag, FraudSeverity


def create_fraud_flag(
    db: Session,
    *,
    company_id: str,
    store_id: str | None,
    sale_id: str | None,
    txid: str | None,
    severity: FraudSeverity,
    flag_type: str,
    description: str,
) -> FraudFlag:
    flag = FraudFlag(
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
