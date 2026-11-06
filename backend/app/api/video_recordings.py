
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter, Depends, File, HTTPException,
    UploadFile, status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.camera import Camera
from app.models.parking_site import ParkingSite
from app.models.video_recording import VideoRecording


router = APIRouter(
    prefix=(
        "/organisations/{organisation_id}"
        "/sites/{site_id}"
        "/cameras/{camera_id}/recordings"
    ),
    tags=["Video Recordings"],
)

DbSession = Annotated[Session, Depends(get_db)]

STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "videos"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_recording(
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    camera_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    db: DbSession,
):
    camera = db.scalar(
        select(Camera)
        .join(ParkingSite, Camera.site_id == ParkingSite.id)
        .where(
            Camera.id == camera_id,
            Camera.site_id == site_id,
            ParkingSite.organisation_id == organisation_id,
            ParkingSite.status == "active",
            Camera.status == "active",
        )
    )

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail="Active camera not found at this site",
        )

    filename = Path(file.filename or "").name

    if (
        not filename.lower().endswith(".mp4")
        or len(filename) > 255
    ):
        raise HTTPException(
            status_code=422,
            detail="Only MP4 files are accepted",
        )

    recording_id = uuid.uuid4()
    storage_key = f"{recording_id}.mp4"
    destination = STORAGE_DIR / storage_key

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    total_bytes = 0

    try:
        with destination.open("xb") as output:
            while chunk := file.file.read(CHUNK_SIZE):
                total_bytes += len(chunk)

                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Maximum upload size is 100 MB",
                    )

                output.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=422,
                detail="Empty files are not accepted",
            )

        with destination.open("rb") as saved_file:
            header = saved_file.read(12)

        if len(header) < 12 or header[4:8] != b"ftyp":
            raise HTTPException(
                status_code=422,
                detail="Invalid MP4 container header",
            )

        recording = VideoRecording(
            id=recording_id,
            camera_id=camera_id,
            original_filename=filename,
            storage_key=storage_key,
            file_size_bytes=total_bytes,
            status="uploaded",
        )

        db.add(recording)
        db.commit()
        db.refresh(recording)

        return {
            "id": recording.id,
            "camera_id": recording.camera_id,
            "original_filename": recording.original_filename,
            "file_size_bytes": recording.file_size_bytes,
            "status": recording.status,
            "created_at": recording.created_at,
        }

    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise

    finally:
        file.file.close()
