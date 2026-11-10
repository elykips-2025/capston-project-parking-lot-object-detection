
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganisationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    @field_validator("name", mode="before")
    @classmethod
    def normalise_name(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class OrganisationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
