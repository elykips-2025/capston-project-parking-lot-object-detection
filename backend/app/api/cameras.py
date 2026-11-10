
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

import io
import os
import tempfile
from pathlib import Path

from fastapi import File, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func

from app.models.parking_bay import ParkingBay


router = APIRouter(
    prefix="/organisations/{organisation_id}/sites/{site_id}/cameras",
    tags=["Cameras"],
)

DbSession = Annotated[Session, Depends(get_db)]
BACKEND_ROOT = Path(__file__).resolve().parents[2]

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

    backend_root = BACKEND_ROOT

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

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_FORMATS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
}


@router.put("/{camera_id}/reference-image")
def upload_camera_reference_image(
    membership: RequireOrganisationAdmin,
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    camera_id: uuid.UUID,
    db: DbSession,
    file: UploadFile = File(...),
):
    verify_site(db, organisation_id, site_id)

    camera = db.scalar(
        select(Camera)
        .where(
            Camera.id == camera_id,
            Camera.site_id == site_id,
        )
        .with_for_update()
    )

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail="Camera not found",
        )

    if camera.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Cannot configure an inactive camera",
        )

    # Read at most one byte beyond the permitted limit.
    content = file.file.read(MAX_IMAGE_BYTES + 1)

    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Reference image exceeds 10 MB",
        )

    try:
        with Image.open(io.BytesIO(content)) as image:
            image_format = image.format

            if image_format not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=422,
                    detail="Only JPEG and PNG images are supported",
                )

            width, height = image.size

            if (
                width <= 0
                or height <= 0
                or width * height > MAX_IMAGE_PIXELS
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Invalid or oversized image dimensions",
                )

            image.verify()

    except HTTPException:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid or corrupted image",
        ) from exc

    # A replacement must preserve the coordinate system
    # whenever the camera already has mapped parking bays.
    bay_count = db.scalar(
        select(func.count(ParkingBay.id)).where(
            ParkingBay.camera_id == camera_id,
            ParkingBay.site_id == site_id,
        )
    )

    if bay_count:
        raise HTTPException(
            status_code=409,
            detail=(
                "Camera already has mapped parking bays. "
                "Reference-image replacement requires a "
                "mapping-preservation workflow."
            ),
        )

    extension, _ = ALLOWED_FORMATS[image_format]

    backend_root = BACKEND_ROOT

    relative_directory = (
        Path("storage") / "camera-references" / str(camera_id)
    )

    target_directory = backend_root / relative_directory
    target_directory.mkdir(parents=True, exist_ok=True)

    # Each upload receives a new filename. Existing files
    # remain untouched until the new configuration is committed.
    filename = f"{uuid.uuid4().hex}{extension}"
    target_path = target_directory / filename

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target_directory,
            prefix=".upload-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, target_path)
        temporary_path = None

        storage_key = str(relative_directory / filename)

        camera.reference_image_storage_key = storage_key
        db.commit()

    except Exception:
        db.rollback()

        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

        target_path.unlink(missing_ok=True)
        raise

    return {
        "camera_id": str(camera.id),
        "reference_image_storage_key": storage_key,
        "width": width,
        "height": height,
        "format": image_format,
    }