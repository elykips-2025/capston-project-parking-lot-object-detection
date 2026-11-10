import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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
from app.models.parking_bay import ParkingBay
from app.models.occupancy_observation import OccupancyObservation

router = APIRouter(
    prefix="/organisations/{organisation_id}/sites/{site_id}/cameras/{camera_id}/parking-bays",
    tags=["Parking Bays"],
)
DbSession = Annotated[Session, Depends(get_db)]


class Point(BaseModel):
    x: float
    y: float


class BayInput(BaseModel):
    id: str = Field(min_length=1, max_length=30)
    points: list[Point] = Field(min_length=4, max_length=4)


class MappingInput(BaseModel):
    bays: list[BayInput] = Field(max_length=1000)


def get_camera(db, organisation_id, site_id, camera_id):
    site = db.scalar(select(ParkingSite).where(
        ParkingSite.id == site_id,
        ParkingSite.organisation_id == organisation_id,
    ))
    if site is None:
        raise HTTPException(404, "Parking site not found")

    camera = db.scalar(select(Camera).where(
        Camera.id == camera_id,
        Camera.site_id == site_id,
    ))
    if camera is None:
        raise HTTPException(404, "Camera not found")
    return site, camera


@router.get("")
def list_bays(
    membership: RequireOrganisationViewer,
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    camera_id: uuid.UUID,
    db: DbSession,
):
    get_camera(db, organisation_id, site_id, camera_id)
    rows = db.scalars(select(ParkingBay).where(
        ParkingBay.site_id == site_id,
        ParkingBay.camera_id == camera_id,
    ).order_by(ParkingBay.bay_code)).all()
    return {
        "bays": [
            {"id": row.bay_code, "points": row.polygon}
            for row in rows
        ]
    }


@router.put("")
def save_bays(
    membership: RequireOrganisationAdmin,
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    camera_id: uuid.UUID,
    payload: MappingInput,
    db: DbSession,
):
    site, camera = get_camera(db, organisation_id, site_id, camera_id)

    if site.status != "active" or camera.status != "active":
        raise HTTPException(409, "Site or camera is inactive")
    if not camera.reference_image_storage_key:
        raise HTTPException(409, "Upload a camera reference image first")

    codes = [bay.id for bay in payload.bays]
    if len(codes) != len(set(codes)):
        raise HTTPException(422, "Duplicate bay codes")

    for bay in payload.bays:
        points = bay.points
        if any(not math.isfinite(p.x) or not math.isfinite(p.y)
               or p.x < 0 or p.y < 0 for p in points):
            raise HTTPException(422, f"Invalid coordinates: {bay.id}")

        area = abs(sum(
            points[i].x * points[(i + 1) % 4].y
            - points[(i + 1) % 4].x * points[i].y
            for i in range(4)
        )) / 2
        if area <= 1:
            raise HTTPException(422, f"Invalid polygon: {bay.id}")

    # Serialize mapping saves for this camera.
    camera = db.scalar(select(Camera).where(
        Camera.id == camera_id,
        Camera.site_id == site_id,
    ).with_for_update())

    existing = {
        bay.bay_code: bay
        for bay in db.scalars(select(ParkingBay).where(
            ParkingBay.camera_id == camera_id,
            ParkingBay.site_id == site_id,
        )).all()
    }

    requested = set(codes)

    for code, row in existing.items():
        changed = (
            code not in requested or
            row.polygon != [
                {"x": p.x, "y": p.y}
                for p in next(b for b in payload.bays if b.id == code).points
            ]
        )

        if changed:
            observed = db.scalar(select(OccupancyObservation.id).where(
                OccupancyObservation.bay_id == row.id
            ).limit(1))
            if observed is not None:
                raise HTTPException(
                    409,
                    f"Bay {code} has occupancy history and cannot be modified or deleted",
                )

    # Bay codes must remain unique across the entire site.
    conflicts = db.scalars(select(ParkingBay).where(
        ParkingBay.site_id == site_id,
        ParkingBay.camera_id != camera_id,
        ParkingBay.bay_code.in_(codes),
    )).all()
    if conflicts:
        raise HTTPException(409, "Bay code belongs to another camera")

    for code, row in existing.items():
        if code not in requested:
            db.delete(row)

    for bay in payload.bays:
        polygon = [{"x": p.x, "y": p.y} for p in bay.points]
        if bay.id in existing:
            existing[bay.id].polygon = polygon
        else:
            db.add(ParkingBay(
                site_id=site_id,
                camera_id=camera_id,
                bay_code=bay.id,
                bay_type="standard",
                polygon=polygon,
            ))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Parking-bay configuration conflict")

    return {"saved": len(payload.bays), "bays": [
        {"id": bay.id, "points": [
            {"x": p.x, "y": p.y} for p in bay.points
        ]} for bay in payload.bays
    ]}
