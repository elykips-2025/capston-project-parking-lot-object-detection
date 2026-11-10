from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.organisation import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.user import User
from app.schemas.organisation import (
    OrganisationCreate,
    OrganisationResponse,
)

router = APIRouter(
    prefix="/organisations",
    tags=["Organisations"],
)

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=list[OrganisationResponse])
def list_organisations(
    user: CurrentUser,
    db: DbSession,
):
    statement = (
        select(Organisation)
        .join(
            OrganisationMembership,
            OrganisationMembership.organisation_id == Organisation.id,
        )
        .where(OrganisationMembership.user_id == user.id)
        .order_by(Organisation.created_at, Organisation.id)
    )

    return list(db.scalars(statement).all())


@router.post(
    "",
    response_model=OrganisationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organisation(
    payload: OrganisationCreate,
    user: CurrentUser,
    db: DbSession,
):
    organisation = Organisation(
        name=payload.name.strip(),
    )

    db.add(organisation)
    db.flush()

    membership = OrganisationMembership(
        organisation_id=organisation.id,
        user_id=user.id,
        role="owner",
    )

    db.add(membership)
    db.commit()
    db.refresh(organisation)

    return organisation