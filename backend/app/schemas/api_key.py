from datetime import datetime
import uuid
from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(..., max_length=100, description="Friendly descriptive name for the API key.")


class ApiKeyOut(BaseModel):
    id: uuid.UUID
    name: str
    masked_key: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreatedOut(ApiKeyOut):
    raw_key: str = Field(
        ...,
        description="The unmasked API key. Show this ONLY ONCE as it is hashed in the database and cannot be recovered.",
    )
