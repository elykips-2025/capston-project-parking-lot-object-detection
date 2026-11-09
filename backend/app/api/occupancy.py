
import uuid
from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.authorisation import RequireOrganisationViewer
from app.models import (
    Camera,
    OccupancyObservation,
    ParkingBay,
    ParkingSite,
    VideoRecording,
)

router = APIRouter(
    prefix="/organisations/{organisation_id}/sites/{site_id}/occupancy",
    tags=["Occupancy"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def get_site_occupancy(
    membership: RequireOrganisationViewer,
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    recording_id: uuid.UUID,
    db: DbSession,
    timestamp_seconds: Annotated[
        float | None,
        Query(ge=0, allow_inf_nan=False),
    ] = None,
):
    site = db.scalar(
        select(ParkingSite).where(
            ParkingSite.id == site_id,
            ParkingSite.organisation_id == organisation_id,
        )
    )

    if site is None:
        raise HTTPException(404, "Parking site not found")

    recording = db.scalar(
        select(VideoRecording)
        .join(Camera, Camera.id == VideoRecording.camera_id)
        .where(
            VideoRecording.id == recording_id,
            Camera.site_id == site_id,
        )
    )

    if recording is None:
        raise HTTPException(
            404,
            "Recording not found for this parking site",
        )

    selected_timestamp = timestamp_seconds

    if selected_timestamp is None:
        selected_timestamp = db.scalar(
            select(func.max(OccupancyObservation.timestamp_seconds))
            .where(OccupancyObservation.recording_id == recording_id)
        )

    if selected_timestamp is None:
        raise HTTPException(
            404,
            "No occupancy observations for this recording",
        )

    rows = db.execute(
        select(ParkingBay, OccupancyObservation)
        .join(
            OccupancyObservation,
            OccupancyObservation.bay_id == ParkingBay.id,
        )
        .where(
            ParkingBay.site_id == site_id,
            ParkingBay.camera_id == recording.camera_id,
            OccupancyObservation.recording_id == recording_id,
            OccupancyObservation.timestamp_seconds == selected_timestamp,
        )
        .order_by(ParkingBay.bay_code)
    ).all()

    if not rows:
        raise HTTPException(
            404,
            "No occupancy observations at the requested timestamp",
        )

    counts = Counter(
        observation.temporal_state
        for _, observation in rows
    )

    return {
        "site_id": site_id,
        "recording_id": recording_id,
        "source": "recorded_video",
        "timestamp_seconds": selected_timestamp,
        "summary": {
            "total": len(rows),
            "available": counts["empty"],
            "occupied": counts["occupied"],
            "unknown": counts["unknown"],
        },
        "bays": [
            {
                "id": bay.id,
                "code": bay.bay_code,
                "type": bay.bay_type,
                "polygon": bay.polygon,
                "raw_state": observation.raw_state,
                "state": observation.temporal_state,
                "occupied_probability": observation.occupied_probability,
                "available": observation.temporal_state == "empty",
            }
            for bay, observation in rows
        ],
    }


@router.get("/history")
def get_site_occupancy_history(
    membership: RequireOrganisationViewer,
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    recording_id: uuid.UUID,
    db: DbSession,
):
    site = db.scalar(
        select(ParkingSite).where(
            ParkingSite.id == site_id,
            ParkingSite.organisation_id == organisation_id,
        )
    )

    if site is None:
        raise HTTPException(404, "Parking site not found")

    recording = db.scalar(
        select(VideoRecording)
        .join(Camera, Camera.id == VideoRecording.camera_id)
        .where(
            VideoRecording.id == recording_id,
            Camera.site_id == site_id,
        )
    )

    if recording is None:
        raise HTTPException(
            404,
            "Recording not found for this parking site",
        )

    rows = db.execute(
        select(
            OccupancyObservation.timestamp_seconds,
            OccupancyObservation.temporal_state,
            func.count(OccupancyObservation.id),
        )
        .join(
            ParkingBay,
            ParkingBay.id == OccupancyObservation.bay_id,
        )
        .where(
            OccupancyObservation.recording_id == recording_id,
            ParkingBay.site_id == site_id,
            ParkingBay.camera_id == recording.camera_id,
        )
        .group_by(
            OccupancyObservation.timestamp_seconds,
            OccupancyObservation.temporal_state,
        )
        .order_by(OccupancyObservation.timestamp_seconds)
    ).all()

    if not rows:
        raise HTTPException(
            404,
            "No occupancy observations for this recording",
        )

    history = {}

    for timestamp, state, count in rows:
        if timestamp not in history:
            history[timestamp] = {
                "timestamp_seconds": timestamp,
                "available": 0,
                "occupied": 0,
                "unknown": 0,
                "total": 0,
            }

        if state == "empty":
            history[timestamp]["available"] += count
        elif state == "occupied":
            history[timestamp]["occupied"] += count
        else:
            history[timestamp]["unknown"] += count

        history[timestamp]["total"] += count

    return {
        "site_id": site_id,
        "recording_id": recording_id,
        "source": "recorded_video",
        "history": list(history.values()),
    }