
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.authorisation import (
    RequireOrganisationAdmin,
    RequireOrganisationViewer,
)
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
    membership: RequireOrganisationAdmin,
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
    membership: RequireOrganisationViewer,
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


@router.get("/{camera_id}/reference-image")
def get_camera_reference_image(
    membership: RequireOrganisationViewer,
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    camera_id: uuid.UUID,
    db: DbSession,
):
    from pathlib import Path
    from fastapi.responses import FileResponse

    verify_site(db, organisation_id, site_id)

    camera = db.scalar(
        select(Camera).where(
            Camera.id == camera_id,
            Camera.site_id == site_id,
        )
    )

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail="Camera not found",
        )

    backend_root = Path(__file__).resolve().parents[2]

    if not camera.reference_image_storage_key:
        raise HTTPException(
            status_code=404,
            detail="Reference image not configured",
        )

    storage_key = Path(camera.reference_image_storage_key)

    if storage_key.is_absolute():
        raise HTTPException(
            status_code=404,
            detail="Reference image not found",
        )

    image_path = (
        backend_root / storage_key
    ).resolve()

    # Reference images must reside in the designated dataset
    # or storage directory, never an arbitrary backend path.
    allowed_roots = (
        (backend_root / "datasets").resolve(),
        (backend_root / "storage").resolve(),
    )

    if not any(
        image_path.is_relative_to(root)
        for root in allowed_roots
    ):
        raise HTTPException(
            status_code=404,
            detail="Reference image not found",
        )

    if not image_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Reference image not found",
        )

    if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise HTTPException(
            status_code=404,
            detail="Unsupported reference image",
        )

    media_type = (
        "image/png"
        if image_path.suffix.lower() == ".png"
        else "image/jpeg"
    )

    return FileResponse(
        path=image_path,
        media_type=media_type,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )
