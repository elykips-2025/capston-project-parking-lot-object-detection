import csv
import math
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Camera, OccupancyObservation, ParkingBay, VideoRecording


CSV_PATH = Path("datasets/video-mapping/video-occupancy-results.csv")
RECORDING_ID = uuid.UUID("424b3b3c-2c4f-4450-8a6d-8c4e60452425")

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


def import_observations(
    recording_id: uuid.UUID,
    csv_path: Path,
    db: Session,
) -> dict:
    """Validate and stage occupancy observations without committing."""
    recording = db.get(VideoRecording, recording_id)
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
    if not bays or len(bay_lookup) != len(bays):
        raise ValueError("Missing or duplicate mapped parking bays")

    with Path(csv_path).open(newline="") as file:
        reader = csv.DictReader(file)
        if not EXPECTED_COLUMNS.issubset(reader.fieldnames or []):
            raise ValueError("CSV is missing required columns")
        rows = list(reader)

    if not rows:
        raise ValueError("CSV contains no observations")

    validated = []
    seen = set()
    snapshots = {}

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

        if parse_boolean(row["available"]) != (raw_state == "empty"):
            raise ValueError(f"Raw availability mismatch: {code}")

        if parse_boolean(row["temporal_available"]) != (
            temporal_state == "empty"
        ):
            raise ValueError(f"Temporal availability mismatch: {code}")

        bay_id = bay_lookup[code].id
        key = (bay_id, timestamp)

        if key in seen:
            raise ValueError(
                f"Duplicate CSV observation: {code}, {timestamp}"
            )

        seen.add(key)
        snapshots.setdefault(timestamp, set()).add(bay_id)
        validated.append((
            bay_id,
            timestamp,
            raw_state,
            temporal_state,
            probability,
        ))

    expected_bay_ids = {bay.id for bay in bays}

    for timestamp, observed_bays in snapshots.items():
        if observed_bays != expected_bay_ids:
            raise ValueError(
                f"Incomplete snapshot at {timestamp} seconds"
            )

    existing_rows = db.scalars(
        select(OccupancyObservation).where(
            OccupancyObservation.recording_id == recording_id
        )
    ).all()

    existing = {
        (observation.bay_id, observation.timestamp_seconds): observation
        for observation in existing_rows
    }

    created = 0
    skipped = 0

    # Validate conflicts before staging any inserts.
    for bay_id, timestamp, raw, temporal, probability in validated:
        previous = existing.get((bay_id, timestamp))
        if previous is None:
            continue

        if (
            previous.raw_state != raw
            or previous.temporal_state != temporal
            or not math.isclose(
                previous.occupied_probability,
                probability,
                rel_tol=0,
                abs_tol=1e-9,
            )
        ):
            raise ValueError(
                f"Conflicting observation: {bay_id}, {timestamp}"
            )

    for bay_id, timestamp, raw, temporal, probability in validated:
        if (bay_id, timestamp) in existing:
            skipped += 1
            continue

        db.add(OccupancyObservation(
            recording_id=recording_id,
            bay_id=bay_id,
            timestamp_seconds=timestamp,
            raw_state=raw,
            temporal_state=temporal,
            occupied_probability=probability,
        ))
        created += 1

    return {
        "created": created,
        "skipped": skipped,
        "total": len(validated),
        "timestamps": len(snapshots),
        "bays": len(bays),
    }


def main():
    with SessionLocal.begin() as db:
        result = import_observations(
            recording_id=RECORDING_ID,
            csv_path=CSV_PATH,
            db=db,
        )

    print(f"CSV observations: {result['total']}")
    print(f"Created: {result['created']}")
    print(f"Skipped existing: {result['skipped']}")


if __name__ == "__main__":
    main()
