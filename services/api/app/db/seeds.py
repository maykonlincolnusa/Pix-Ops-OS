from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, Tenant, TenantStatus


def seed_demo_data(db: Session) -> dict:
    tenant = db.scalar(select(Tenant).where(Tenant.document_number == "12345678000190"))
    if tenant:
        return {"tenant_id": tenant.id, "company_id": None, "status": "already_seeded"}

    tenant = Tenant(
        name="Tenant Demo PixOps",
        document_number="12345678000190",
        plan="pro",
        status=TenantStatus.ACTIVE.value,
    )
    db.add(tenant)
    db.flush()

    company = Company(
        tenant_id=tenant.id,
        name="Empresa Demo PixOps",
        legal_name="Empresa Demo PixOps LTDA",
        tax_id="12345678000190",
    )
    db.add(company)
    db.commit()
    return {"tenant_id": tenant.id, "company_id": company.id, "status": "seeded"}
