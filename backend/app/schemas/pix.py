from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class PixChargeCreate(BaseModel):
    company_id: str
    sale_id: str
    pix_key: str = Field(min_length=5, max_length=120)
    payer_name: str | None = Field(default=None, max_length=160)
    expires_in_minutes: int = Field(default=20, ge=1, le=180)


class PixChargeRead(BaseSchema):
    id: str
    company_id: str
    sale_id: str
    txid: str
    pix_key: str
    amount_cents: int
    payer_name: str | None
    qr_code_text: str
    qr_code_base64: str | None
    status: str
    expires_at: datetime
    confirmed_at: datetime | None
    confirmed_amount_cents: int | None
    end_to_end_id: str | None
    created_at: datetime


class PixWebhookPayload(BaseModel):
    company_id: str | None = None
    txid: str = Field(min_length=4, max_length=36)
    end_to_end_id: str = Field(min_length=4, max_length=64)
    amount_cents: int = Field(gt=0, le=500000000)
    payer_document: str | None = Field(default=None, max_length=20)
    paid_at: datetime | None = None
    raw_payload: dict = Field(default_factory=dict)


class PixWebhookResult(BaseSchema):
    txid: str
    sale_id: str | None
    status: str
    reconciliation_status: str | None
    fraud_flag_id: str | None
