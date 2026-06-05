from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class CompanyCreate(BaseModel):
    tenant_id: str
    name: str = Field(min_length=2, max_length=160)
    legal_name: str = Field(min_length=2, max_length=200)
    tax_id: str = Field(min_length=11, max_length=20, description="CNPJ sem máscara ou com máscara.")


class CompanyRead(BaseSchema):
    id: str
    tenant_id: str
    name: str
    legal_name: str
    tax_id: str
    created_at: datetime
