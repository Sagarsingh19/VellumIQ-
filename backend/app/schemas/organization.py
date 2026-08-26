from uuid import UUID
from pydantic import BaseModel


class OrganizationBase(BaseModel):
    name: str


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: UUID

    class Config:
        from_attributes = True
