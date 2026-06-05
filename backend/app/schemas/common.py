from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseSchema):
    message: str


class IdResponse(BaseSchema):
    id: str


class TimestampedSchema(BaseSchema):
    created_at: datetime
