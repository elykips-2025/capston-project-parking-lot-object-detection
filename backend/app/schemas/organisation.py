
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganisationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class OrganisationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
