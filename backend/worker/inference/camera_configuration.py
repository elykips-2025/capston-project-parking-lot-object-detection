from pathlib import Path
import uuid

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Camera, ParkingBay
from worker.inference.rectify_mapped_bays import extract_points


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def resolve_reference_image(storage_key: str) -> Path:
    """Resolve a reference image safely within the backend directory."""

    if not storage_key:
        raise ValueError("Camera has no reference image configured")

    root = BACKEND_ROOT.resolve()
    image_path = (root / storage_key).resolve()

    if not image_path.is_relative_to(root):
        raise ValueError("Reference image path escapes backend directory")

    if not image_path.is_file():
        raise FileNotFoundError(
            f"Reference image not found: {storage_key}"
        )

    return image_path


def load_camera_configuration(
    db: Session,
    camera_id: uuid.UUID,
):
    """Load a camera's reference image and database-backed bay polygons."""

    camera = db.scalar(
        select(Camera).where(Camera.id == camera_id)
    )

    if camera is None:
        raise LookupError("Camera not found")

    if camera.status != "active":
        raise ValueError("Camera is inactive")

    image_path = resolve_reference_image(
        camera.reference_image_storage_key
    )

    reference = cv2.imread(str(image_path))

    if reference is None or reference.size == 0:
        raise ValueError("Unable to decode camera reference image")

    height, width = reference.shape[:2]

    camera_bays = db.scalars(
        select(ParkingBay)
        .where(
            ParkingBay.camera_id == camera.id,
            ParkingBay.site_id == camera.site_id,
        )
        .order_by(ParkingBay.bay_code)
    ).all()

    if not camera_bays:
        raise ValueError("Camera has no mapped parking bays")

    bays = []
    seen_codes = set()

    for bay in camera_bays:
        if bay.bay_code in seen_codes:
            raise ValueError(
                f"Duplicate parking bay code: {bay.bay_code}"
            )

        seen_codes.add(bay.bay_code)

        try:
            points = extract_points({"polygon": bay.polygon})
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise ValueError(
                f"Invalid polygon for bay {bay.bay_code}: {exc}"
            ) from exc

        if not np.isfinite(points).all():
            raise ValueError(
                f"Bay {bay.bay_code} contains non-finite coordinates"
            )

        if (
            (points[:, 0] < 0).any()
            or (points[:, 0] >= width).any()
            or (points[:, 1] < 0).any()
            or (points[:, 1] >= height).any()
        ):
            raise ValueError(
                f"Bay {bay.bay_code} extends outside "
                f"reference image ({width}x{height})"
            )

        area = abs(
            np.dot(points[:, 0], np.roll(points[:, 1], 1))
            - np.dot(points[:, 1], np.roll(points[:, 0], 1))
        ) / 2

        if area <= 1:
            raise ValueError(
                f"Bay {bay.bay_code} has degenerate geometry"
            )

        bays.append({
            "id": bay.bay_code,
            "polygon": bay.polygon,
        })

    return camera, reference, bays
