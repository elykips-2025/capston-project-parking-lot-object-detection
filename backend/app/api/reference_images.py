from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(
    prefix="/reference-images",
    tags=["Reference Images"],
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]

DEMO_REFERENCE_IMAGE = (
    BACKEND_ROOT
    / "datasets"
    / "video-mapping"
    / "reference-frame.jpg"
)


@router.get("/demo")
def get_demo_reference_image():
    if not DEMO_REFERENCE_IMAGE.is_file():
        raise HTTPException(
            status_code=404,
            detail="Reference image not found",
        )

    return FileResponse(
        path=DEMO_REFERENCE_IMAGE,
        media_type="image/jpeg",
        filename="reference-frame.jpg",
        content_disposition_type="inline",
    )
