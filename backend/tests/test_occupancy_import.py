import csv
import uuid

import pytest

from sqlalchemy import create_engine, func, select, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    Camera,
    OccupancyObservation,
    Organisation,
    ParkingBay,
    ParkingSite,
    VideoRecording,
)
from worker.import_occupancy_observations import import_observations


def test_import_observations_for_arbitrary_recording(tmp_path):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    recording_id = uuid.uuid4()
    camera_id = uuid.uuid4()
    site_id = uuid.uuid4()
    organisation_id = uuid.uuid4()

    try:
        with Session.begin() as db:
            db.add(Organisation(
                id=organisation_id,
                name="Importer Test Organisation",
            ))
            db.flush()

            db.add(ParkingSite(
                id=site_id,
                organisation_id=organisation_id,
                name="Importer Test Site",
            ))
            db.flush()

            db.add(Camera(
                id=camera_id,
                site_id=site_id,
                name="Importer Test Camera",
            ))
            db.flush()

            db.add(VideoRecording(
                id=recording_id,
                camera_id=camera_id,
                original_filename="sample.mp4",
                storage_key=f"tests/{recording_id}.mp4",
                file_size_bytes=1024,
            ))

            for code in ("A01", "A02"):
                db.add(ParkingBay(
                    id=uuid.uuid4(),
                    site_id=site_id,
                    camera_id=camera_id,
                    bay_code=code,
                    bay_type="standard",
                    polygon=[
                        {"x": 0, "y": 0},
                        {"x": 10, "y": 0},
                        {"x": 10, "y": 10},
                        {"x": 0, "y": 10},
                    ],
                ))

        csv_path = tmp_path / "occupancy.csv"

        with csv_path.open("w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "timestamp_seconds",
                    "bay_id",
                    "state",
                    "occupied_probability",
                    "available",
                    "temporal_state",
                    "temporal_available",
                ],
            )
            writer.writeheader()

            for timestamp in (0.0, 1.0):
                writer.writerow({
                    "timestamp_seconds": timestamp,
                    "bay_id": "A01",
                    "state": "empty",
                    "occupied_probability": 0.1,
                    "available": True,
                    "temporal_state": "empty",
                    "temporal_available": True,
                })
                writer.writerow({
                    "timestamp_seconds": timestamp,
                    "bay_id": "A02",
                    "state": "occupied",
                    "occupied_probability": 0.9,
                    "available": False,
                    "temporal_state": "occupied",
                    "temporal_available": False,
                })

        with Session.begin() as db:
            result = import_observations(
                recording_id=recording_id,
                csv_path=csv_path,
                db=db,
            )

        assert result["created"] == 4
        assert result["skipped"] == 0

        # Re-importing identical observations must not create duplicates.
        with Session.begin() as db:
            repeated = import_observations(
                recording_id=recording_id,
                csv_path=csv_path,
                db=db,
            )

        assert repeated["created"] == 0
        assert repeated["skipped"] == 4

        # A changed prediction must not overwrite stored observations.
        original_csv = csv_path.read_text()
        csv_path.write_text(
            original_csv.replace(",0.1,True,", ",0.2,True,", 1)
        )

        with pytest.raises(ValueError, match="Conflicting observation"):
            with Session.begin() as db:
                import_observations(
                    recording_id=recording_id,
                    csv_path=csv_path,
                    db=db,
                )

        # Reject a timestamp missing one of the camera's parking bays.
        with csv_path.open("w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "timestamp_seconds",
                    "bay_id",
                    "state",
                    "occupied_probability",
                    "available",
                    "temporal_state",
                    "temporal_available",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "timestamp_seconds": 2.0,
                "bay_id": "A01",
                "state": "empty",
                "occupied_probability": 0.1,
                "available": True,
                "temporal_state": "empty",
                "temporal_available": True,
            })

        with pytest.raises(ValueError, match="Incomplete snapshot"):
            with Session.begin() as db:
                import_observations(
                    recording_id=recording_id,
                    csv_path=csv_path,
                    db=db,
                )

        # A successful import must remain rollback-safe.
        csv_path.write_text(original_csv)

        with Session() as db:
            db.query(OccupancyObservation).filter(
                OccupancyObservation.recording_id == recording_id
            ).delete()
            db.flush()

            result = import_observations(
                recording_id=recording_id,
                csv_path=csv_path,
                db=db,
            )

            assert result["created"] == 4
            db.flush()

            staged_count = db.scalar(
                select(func.count(OccupancyObservation.id)).where(
                    OccupancyObservation.recording_id == recording_id
                )
            )
            assert staged_count == 4

            # Roll back both the deletion and the newly staged rows.
            db.rollback()

        with Session() as db:
            count = db.scalar(
                select(func.count(OccupancyObservation.id)).where(
                    OccupancyObservation.recording_id == recording_id
                )
            )
            assert count == 4

            observations = db.scalars(
                select(OccupancyObservation).where(
                    OccupancyObservation.recording_id == recording_id
                )
            ).all()

            assert len(observations) == 4
            assert sorted(
                observation.occupied_probability
                for observation in observations
            ) == [0.1, 0.1, 0.9, 0.9]
    finally:
        engine.dispose()
