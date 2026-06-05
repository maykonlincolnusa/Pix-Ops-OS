from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DBSession, MasterApiKeyDep
from app.db.models import CashRegister, Company, Operator, Store, Tenant, TenantStatus
from app.schemas.cash_register import CashRegisterCreate, CashRegisterRead
from app.schemas.company import CompanyCreate, CompanyRead
from app.schemas.operator import OperatorCreate, OperatorRead
from app.schemas.store import StoreCreate, StoreRead
from app.schemas.tenant import TenantCreate, TenantRead
from app.db.seeds import seed_demo_data
from app.services.event_catalog import EventType
from app.services.ledger import append_event

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post("/tenants", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
def create_tenant(_: MasterApiKeyDep, payload: TenantCreate, db: DBSession) -> Tenant:
    tenant = Tenant(
        name=payload.name,
        document_number=payload.document_number,
        plan=payload.plan,
        status=TenantStatus.ACTIVE.value,
    )
    db.add(tenant)
    try:
        db.flush()
        append_event(
            db,
            tenant_id=tenant.id,
            aggregate_type="tenant",
            aggregate_id=tenant.id,
            event_type=EventType.TENANT_CREATED.value,
            payload={"name": tenant.name, "document_number": tenant.document_number, "plan": tenant.plan},
            source="system",
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tenant already exists for this document.") from exc
    return tenant


@router.get("/tenants", response_model=list[TenantRead])
def list_tenants(_: MasterApiKeyDep, db: DBSession) -> list[Tenant]:
    return db.scalars(select(Tenant).order_by(Tenant.created_at.desc())).all()


@router.post("/seed")
def seed(_: MasterApiKeyDep, db: DBSession) -> dict:
    return seed_demo_data(db)


@router.post("/companies", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(_: MasterApiKeyDep, payload: CompanyCreate, db: DBSession) -> Company:
    tenant = db.scalar(select(Tenant).where(Tenant.id == payload.tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    company = Company(
        tenant_id=payload.tenant_id,
        name=payload.name,
        legal_name=payload.legal_name,
        tax_id=payload.tax_id,
    )
    db.add(company)
    try:
        db.flush()
        append_event(
            db,
            tenant_id=company.tenant_id,
            aggregate_type="organization",
            aggregate_id=company.id,
            event_type="organization.created",
            payload={"name": company.name, "tax_id": company.tax_id},
            source="system",
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Company already exists for this tax ID.") from exc
    return company


@router.get("/companies", response_model=list[CompanyRead])
def list_companies(_: MasterApiKeyDep, db: DBSession, tenant_id: str = Query(...)) -> list[Company]:
    return db.scalars(
        select(Company).where(Company.tenant_id == tenant_id).order_by(Company.created_at.desc())
    ).all()


@router.post("/stores", response_model=StoreRead, status_code=status.HTTP_201_CREATED)
def create_store(_: MasterApiKeyDep, payload: StoreCreate, db: DBSession) -> Store:
    company = db.scalar(
        select(Company).where(
            Company.id == payload.company_id,
            Company.tenant_id == payload.tenant_id,
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found for this tenant.")

    store = Store(
        tenant_id=payload.tenant_id,
        company_id=payload.company_id,
        name=payload.name,
        code=payload.code,
    )
    db.add(store)
    try:
        db.flush()
        append_event(
            db,
            tenant_id=store.tenant_id,
            aggregate_type="store",
            aggregate_id=store.id,
            event_type=EventType.STORE_CREATED.value,
            payload={"name": store.name, "code": store.code, "company_id": store.company_id},
            source="system",
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Store code already exists for this tenant.") from exc
    return store


@router.get("/stores", response_model=list[StoreRead])
def list_stores(_: MasterApiKeyDep, db: DBSession, tenant_id: str = Query(...), company_id: str = Query(...)) -> list[Store]:
    return db.scalars(
        select(Store)
        .where(Store.tenant_id == tenant_id, Store.company_id == company_id)
        .order_by(Store.created_at.desc())
    ).all()


@router.post("/operators", response_model=OperatorRead, status_code=status.HTTP_201_CREATED)
def create_operator(_: MasterApiKeyDep, payload: OperatorCreate, db: DBSession) -> Operator:
    company = db.scalar(
        select(Company).where(
            Company.id == payload.company_id,
            Company.tenant_id == payload.tenant_id,
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found for this tenant.")
    if payload.store_id:
        store = db.scalar(
            select(Store).where(
                Store.id == payload.store_id,
                Store.company_id == payload.company_id,
                Store.tenant_id == payload.tenant_id,
            )
        )
        if not store:
            raise HTTPException(status_code=404, detail="Store not found for this tenant.")

    operator = Operator(
        tenant_id=payload.tenant_id,
        company_id=payload.company_id,
        store_id=payload.store_id,
        full_name=payload.full_name,
        document=payload.document,
    )
    db.add(operator)
    db.flush()
    append_event(
        db,
        tenant_id=operator.tenant_id,
        aggregate_type="operator",
        aggregate_id=operator.id,
        event_type=EventType.OPERATOR_CREATED.value,
        payload={"full_name": operator.full_name, "store_id": operator.store_id},
        source="system",
    )
    db.commit()
    return operator


@router.get("/operators", response_model=list[OperatorRead])
def list_operators(_: MasterApiKeyDep, db: DBSession, tenant_id: str = Query(...), company_id: str = Query(...)) -> list[Operator]:
    return db.scalars(
        select(Operator)
        .where(Operator.tenant_id == tenant_id, Operator.company_id == company_id)
        .order_by(Operator.created_at.desc())
    ).all()


@router.post("/cash-registers", response_model=CashRegisterRead, status_code=status.HTTP_201_CREATED)
def create_cash_register(_: MasterApiKeyDep, payload: CashRegisterCreate, db: DBSession) -> CashRegister:
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

    cash_register = CashRegister(
        tenant_id=payload.tenant_id,
        company_id=payload.company_id,
        store_id=payload.store_id,
        operator_id=payload.operator_id,
        code=payload.code,
    )
    db.add(cash_register)
    try:
        db.flush()
        append_event(
            db,
            tenant_id=cash_register.tenant_id,
            aggregate_type="cashier",
            aggregate_id=cash_register.id,
            event_type="cashier.created",
            payload={"code": cash_register.code, "store_id": cash_register.store_id},
            source="system",
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cash register code already exists for this store.") from exc
    return cash_register


@router.get("/cash-registers", response_model=list[CashRegisterRead])
def list_cash_registers(
    _: MasterApiKeyDep,
    db: DBSession,
    tenant_id: str = Query(...),
    company_id: str = Query(...),
    store_id: str | None = Query(default=None),
) -> list[CashRegister]:
    query = select(CashRegister).where(
        CashRegister.tenant_id == tenant_id,
        CashRegister.company_id == company_id,
    )
    if store_id:
        query = query.where(CashRegister.store_id == store_id)
    return db.scalars(query.order_by(CashRegister.created_at.desc())).all()
