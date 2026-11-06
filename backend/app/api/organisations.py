
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.organisation import Organisation
from app.schemas.organisation import (
    OrganisationCreate,
    OrganisationResponse,
)

router = APIRouter(
    prefix="/organisations",
    tags=["Organisations"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=OrganisationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organisation(
    payload: OrganisationCreate,
    db: DbSession,
):
    organisation = Organisation(name=payload.name)

    db.add(organisation)
    db.commit()
    db.refresh(organisation)

    return organisation
