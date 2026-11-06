
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ParkingSiteCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    location: str | None = Field(default=None, max_length=255)


class ParkingSiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    name: str
    location: str | None
    status: Literal["active", "inactive"]
    created_at: datetime



class ParkingSiteUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )
    location: str | None = Field(
        default=None,
        max_length=255,
    )
    status: Literal["active", "inactive"] | None = None

