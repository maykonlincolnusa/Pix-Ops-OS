from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import JSON, BigInteger, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def uuid_str() -> str:
    return str(uuid4())


class SaleStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    DIVERGENT = "DIVERGENT"
    CANCELLED = "CANCELLED"


class PixChargeStatus(StrEnum):
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    EXPIRED = "EXPIRED"


class ReconciliationStatus(StrEnum):
    MATCHED = "MATCHED"
    MISSING_PAYMENT = "MISSING_PAYMENT"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    UNEXPECTED_PAYMENT = "UNEXPECTED_PAYMENT"


class FraudSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FraudStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    stores: Mapped[list[Store]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_store_company_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    company: Mapped[Company] = relationship(back_populates="stores")
    operators: Mapped[list[Operator]] = relationship(back_populates="store")
    cash_registers: Mapped[list[CashRegister]] = relationship(back_populates="store")


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    store_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("stores.id"), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    document: Mapped[str | None] = mapped_column(String(20), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    store: Mapped[Store | None] = relationship(back_populates="operators")


class CashRegister(Base):
    __tablename__ = "cash_registers"
    __table_args__ = (
        UniqueConstraint("company_id", "store_id", "code", name="uq_cash_register_store_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False, index=True)
    operator_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("operators.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    store: Mapped[Store] = relationship(back_populates="cash_registers")


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        UniqueConstraint("company_id", "external_ref", name="uq_sale_company_external_ref"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False, index=True)
    cash_register_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cash_registers.id"), nullable=True, index=True
    )
    operator_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("operators.id"), nullable=True, index=True)
    external_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(240), nullable=True)
    expected_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    expected_method: Mapped[str] = mapped_column(String(40), default="PIX")
    status: Mapped[str] = mapped_column(String(30), default=SaleStatus.PENDING.value)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pix_charge: Mapped[PixCharge | None] = relationship(back_populates="sale", uselist=False)


class PixCharge(Base):
    __tablename__ = "pix_charges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    sale_id: Mapped[str] = mapped_column(String(36), ForeignKey("sales.id"), nullable=False, unique=True, index=True)
    txid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    pix_key: Mapped[str] = mapped_column(String(120), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    payer_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    qr_code_text: Mapped[str] = mapped_column(Text, nullable=False)
    qr_code_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=PixChargeStatus.CREATED.value)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_to_end_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    sale: Mapped[Sale] = relationship(back_populates="pix_charge")


class LedgerEvent(Base):
    __tablename__ = "ledger_events"
    __table_args__ = (
        UniqueConstraint("company_id", "sequence_no", name="uq_ledger_company_sequence"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), default=uuid_str, unique=True, nullable=False)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    store_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("stores.id"), nullable=True, index=True)
    sale_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sales.id"), nullable=True, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    reference_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ReconciliationRecord(Base):
    __tablename__ = "reconciliation_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    store_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("stores.id"), nullable=True, index=True)
    sale_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sales.id"), nullable=True, index=True)
    txid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    expected_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    received_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    store_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("stores.id"), nullable=True, index=True)
    sale_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sales.id"), nullable=True, index=True)
    txid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    flag_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=FraudStatus.OPEN.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CashClosureReport(Base):
    __tablename__ = "cash_closure_reports"
    __table_args__ = (
        UniqueConstraint("company_id", "store_id", "business_date", name="uq_cash_closure_company_store_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("stores.id"), nullable=False, index=True)
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
