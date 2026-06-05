from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import ApiKeyDep, DBSession
from app.db.models import CashRegister, Company, Operator, Store
from app.schemas.cash_register import CashRegisterCreate, CashRegisterRead
from app.schemas.company import CompanyCreate, CompanyRead
from app.schemas.operator import OperatorCreate, OperatorRead
from app.schemas.store import StoreCreate, StoreRead
from app.services.ledger import append_ledger_event

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post("/companies", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(_: ApiKeyDep, payload: CompanyCreate, db: DBSession) -> Company:
    company = Company(
        name=payload.name,
        legal_name=payload.legal_name,
        tax_id=payload.tax_id,
    )
    db.add(company)
    try:
        db.flush()
        append_ledger_event(
            db,
            company_id=company.id,
            store_id=None,
            sale_id=None,
            source="SYSTEM",
            event_type="COMPANY_CREATED",
            reference_id=company.id,
            payload={"name": company.name, "tax_id": company.tax_id},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Company already exists for this tax ID.") from exc
    return company


@router.get("/companies", response_model=list[CompanyRead])
def list_companies(_: ApiKeyDep, db: DBSession) -> list[Company]:
    return db.scalars(select(Company).order_by(Company.created_at.desc())).all()


@router.post("/stores", response_model=StoreRead, status_code=status.HTTP_201_CREATED)
def create_store(_: ApiKeyDep, payload: StoreCreate, db: DBSession) -> Store:
    company = db.scalar(select(Company).where(Company.id == payload.company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    store = Store(
        company_id=payload.company_id,
        name=payload.name,
        code=payload.code,
    )
    db.add(store)
    try:
        db.flush()
        append_ledger_event(
            db,
            company_id=store.company_id,
            store_id=store.id,
            sale_id=None,
            source="SYSTEM",
            event_type="STORE_CREATED",
            reference_id=store.id,
            payload={"name": store.name, "code": store.code},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Store code already exists for this company.") from exc
    return store


@router.get("/stores", response_model=list[StoreRead])
def list_stores(_: ApiKeyDep, db: DBSession, company_id: str = Query(...)) -> list[Store]:
    return db.scalars(
        select(Store).where(Store.company_id == company_id).order_by(Store.created_at.desc())
    ).all()


@router.post("/operators", response_model=OperatorRead, status_code=status.HTTP_201_CREATED)
def create_operator(_: ApiKeyDep, payload: OperatorCreate, db: DBSession) -> Operator:
    company = db.scalar(select(Company).where(Company.id == payload.company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    if payload.store_id:
        store = db.scalar(select(Store).where(Store.id == payload.store_id, Store.company_id == payload.company_id))
        if not store:
            raise HTTPException(status_code=404, detail="Store not found for this company.")

    operator = Operator(
        company_id=payload.company_id,
        store_id=payload.store_id,
        full_name=payload.full_name,
        document=payload.document,
    )
    db.add(operator)
    db.flush()
    append_ledger_event(
        db,
        company_id=operator.company_id,
        store_id=operator.store_id,
        sale_id=None,
        source="SYSTEM",
        event_type="OPERATOR_CREATED",
        reference_id=operator.id,
        payload={"full_name": operator.full_name},
    )
    db.commit()
    return operator


@router.get("/operators", response_model=list[OperatorRead])
def list_operators(_: ApiKeyDep, db: DBSession, company_id: str = Query(...)) -> list[Operator]:
    return db.scalars(
        select(Operator).where(Operator.company_id == company_id).order_by(Operator.created_at.desc())
    ).all()


@router.post("/cash-registers", response_model=CashRegisterRead, status_code=status.HTTP_201_CREATED)
def create_cash_register(_: ApiKeyDep, payload: CashRegisterCreate, db: DBSession) -> CashRegister:
    store = db.scalar(select(Store).where(Store.id == payload.store_id, Store.company_id == payload.company_id))
    if not store:
        raise HTTPException(status_code=404, detail="Store not found for this company.")
    if payload.operator_id:
        operator = db.scalar(
            select(Operator).where(Operator.id == payload.operator_id, Operator.company_id == payload.company_id)
        )
        if not operator:
            raise HTTPException(status_code=404, detail="Operator not found for this company.")

    cash_register = CashRegister(
        company_id=payload.company_id,
        store_id=payload.store_id,
        operator_id=payload.operator_id,
        code=payload.code,
    )
    db.add(cash_register)
    try:
        db.flush()
        append_ledger_event(
            db,
            company_id=cash_register.company_id,
            store_id=cash_register.store_id,
            sale_id=None,
            source="SYSTEM",
            event_type="CASH_REGISTER_CREATED",
            reference_id=cash_register.id,
            payload={"code": cash_register.code, "operator_id": cash_register.operator_id},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cash register code already exists for this store.") from exc
    return cash_register


@router.get("/cash-registers", response_model=list[CashRegisterRead])
def list_cash_registers(
    _: ApiKeyDep,
    db: DBSession,
    company_id: str = Query(...),
    store_id: str | None = Query(default=None),
) -> list[CashRegister]:
    query = select(CashRegister).where(CashRegister.company_id == company_id)
    if store_id:
        query = query.where(CashRegister.store_id == store_id)
    return db.scalars(query.order_by(CashRegister.created_at.desc())).all()
