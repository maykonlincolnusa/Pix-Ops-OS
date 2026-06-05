from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.security import validate_api_key
from app.db.session import get_db

DBSession = Annotated[Session, Depends(get_db)]
ApiKeyDep = Annotated[None, Depends(validate_api_key)]
