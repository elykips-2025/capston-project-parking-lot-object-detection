
import csv
import math
import uuid
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import (
    Camera,
    OccupancyObservation,
    ParkingBay,
    VideoRecording,
)


CSV_PATH = Path(
    "datasets/video-mapping/video-occupancy-results.csv"
)

RECORDING_ID = uuid.UUID(
    "424b3b3c-2c4f-4450-8a6d-8c4e60452425"
)

VALID_STATES = {"occupied", "empty", "unknown"}

EXPECTED_COLUMNS = {
    "timestamp_seconds",
    "bay_id",
    "state",
    "occupied_probability",
    "available",
    "temporal_state",
    "temporal_available",
}


def parse_boolean(value):
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"Invalid boolean: {value!r}")


def main():
    with CSV_PATH.open(newline="") as f:
        reader = csv.DictReader(f)

        if not EXPECTED_COLUMNS.issubset(reader.fieldnames or []):
            raise ValueError("CSV is missing required columns")

        rows = list(reader)

    if len(rows) != 783:
        raise ValueError(
            f"Expected 783 observations, found {len(rows)}"
        )

    with SessionLocal.begin() as db:
        recording = db.get(VideoRecording, RECORDING_ID)

        if recording is None:
            raise ValueError("Video recording not found")

        camera = db.get(Camera, recording.camera_id)

        if camera is None:
            raise ValueError("Recording camera not found")

        bays = db.scalars(
            select(ParkingBay).where(
                ParkingBay.site_id == camera.site_id,
                ParkingBay.camera_id == camera.id,
            )
        ).all()

        bay_lookup = {bay.bay_code: bay for bay in bays}

        if len(bay_lookup) != 27:
            raise ValueError("Expected 27 mapped parking bays")

        existing = set(
            db.execute(
                select(
                    OccupancyObservation.bay_id,
                    OccupancyObservation.timestamp_seconds,
                ).where(
                    OccupancyObservation.recording_id == RECORDING_ID
                )
            ).all()
        )

        created = 0
        skipped = 0
        seen = set()

        for row in rows:
            code = row["bay_id"]

            if code not in bay_lookup:
                raise ValueError(f"Unknown parking bay: {code}")

            timestamp = float(row["timestamp_seconds"])
            probability = float(row["occupied_probability"])
            raw_state = row["state"]
            temporal_state = row["temporal_state"]

            if not math.isfinite(timestamp) or timestamp < 0:
                raise ValueError(f"Invalid timestamp for {code}")

            if not math.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError(f"Invalid probability for {code}")

            if raw_state not in VALID_STATES:
                raise ValueError(f"Invalid raw state for {code}")

            if temporal_state not in VALID_STATES:
                raise ValueError(f"Invalid temporal state for {code}")

            if parse_boolean(row["available"]) != (
                raw_state == "empty"
            ):
                raise ValueError(f"Raw availability mismatch: {code}")

            if parse_boolean(row["temporal_available"]) != (
                temporal_state == "empty"
            ):
                raise ValueError(f"Temporal availability mismatch: {code}")

            bay_id = bay_lookup[code].id
            key = (bay_id, timestamp)

            if key in seen:
                raise ValueError(f"Duplicate CSV observation: {code}, {timestamp}")

            seen.add(key)

            if key in existing:
                skipped += 1
                continue

            db.add(
                OccupancyObservation(
                    recording_id=RECORDING_ID,
                    bay_id=bay_id,
                    timestamp_seconds=timestamp,
                    raw_state=raw_state,
                    temporal_state=temporal_state,
                    occupied_probability=probability,
                )
            )
            created += 1

    print(f"CSV observations: {len(rows)}")
    print(f"Created: {created}")
    print(f"Skipped existing: {skipped}")


if __name__ == "__main__":
    main()
