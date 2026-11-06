
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.camera import Camera
from app.models.parking_site import ParkingSite
from app.schemas.camera import CameraCreate, CameraResponse


router = APIRouter(
    prefix="/organisations/{organisation_id}/sites/{site_id}/cameras",
    tags=["Cameras"],
)

DbSession = Annotated[Session, Depends(get_db)]


def verify_site(
    db: Session,
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
) -> ParkingSite:
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

    return site


@router.post(
    "",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_camera(
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    payload: CameraCreate,
    db: DbSession,
):
    site = verify_site(db, organisation_id, site_id)

    if site.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Cannot add cameras to an inactive site",
        )

    camera = Camera(
        site_id=site_id,
        name=payload.name,
        status="active",
    )

    db.add(camera)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A camera with this name already exists at this site",
        )

    db.refresh(camera)
    return camera


@router.get(
    "",
    response_model=list[CameraResponse],
)
def list_cameras(
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    db: DbSession,
):
    verify_site(db, organisation_id, site_id)

    statement = (
        select(Camera)
        .where(Camera.site_id == site_id)
        .order_by(Camera.created_at, Camera.id)
    )

    return list(db.scalars(statement).all())
