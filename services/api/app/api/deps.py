from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_master_api_key
from app.db.models import User
from app.db.session import get_db

DBSession = Annotated[Session, Depends(get_db)]
MasterApiKeyDep = Annotated[None, Depends(require_master_api_key)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_tenant_id_header(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required.")
    return x_tenant_id


TenantHeader = Annotated[str, Depends(get_tenant_id_header)]
