
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.organisation import Organisation
from app.models.parking_site import ParkingSite
from app.schemas.parking_site import (
    ParkingSiteCreate,
    ParkingSiteResponse,
    ParkingSiteUpdate,
)

router = APIRouter(
    prefix="/organisations/{organisation_id}/sites",
    tags=["Parking Sites"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=ParkingSiteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_parking_site(
    organisation_id: uuid.UUID,
    payload: ParkingSiteCreate,
    db: DbSession,
):
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=404,
            detail="Organisation not found",
        )

    site = ParkingSite(
        organisation_id=organisation_id,
        name=payload.name,
        location=payload.location,
        status="active",
    )

    db.add(site)
    db.commit()
    db.refresh(site)

    return site


@router.get(
    "",
    response_model=list[ParkingSiteResponse],
)
def list_parking_sites(
    organisation_id: uuid.UUID,
    db: DbSession,
):
    organisation = db.get(Organisation, organisation_id)

    if organisation is None:
        raise HTTPException(
            status_code=404,
            detail="Organisation not found",
        )

    statement = (
        select(ParkingSite)
        .where(ParkingSite.organisation_id == organisation_id)
        .order_by(ParkingSite.created_at, ParkingSite.id)
    )

    return db.scalars(statement).all()


@router.get(
    "/{site_id}",
    response_model=ParkingSiteResponse,
)
def get_parking_site(
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    db: DbSession,
):
    statement = select(ParkingSite).where(
        ParkingSite.id == site_id,
        ParkingSite.organisation_id == organisation_id,
    )

    site = db.scalar(statement)

    if site is None:
        raise HTTPException(
            status_code=404,
            detail="Parking site not found",
        )

    return site



@router.patch(
    "/{site_id}",
    response_model=ParkingSiteResponse,
)
def update_parking_site(
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    payload: ParkingSiteUpdate,
    db: DbSession,
):
    site = db.scalar(
        select(ParkingSite).where(
            ParkingSite.id == site_id,
            ParkingSite.organisation_id == organisation_id,
        )
    )

    if site is None:
        raise HTTPException(
            status_code=404,
            detail="Parking site not found",
        )

    changes = payload.model_dump(exclude_unset=True)

    if "name" in changes and changes["name"] is None:
        raise HTTPException(
            status_code=422,
            detail="Site name cannot be null",
        )

    if "status" in changes and changes["status"] is None:
        raise HTTPException(
            status_code=422,
            detail="Site status cannot be null",
        )

    for field, value in changes.items():
        setattr(site, field, value)

    db.commit()
    db.refresh(site)

    return site
