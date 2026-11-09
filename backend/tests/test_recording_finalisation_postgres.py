import csv
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app.models import (
    Camera,
    OccupancyObservation,
    Organisation,
    ParkingBay,
    ParkingSite,
    VideoRecording,
)
from worker import recording_processing_service as service


@pytest.fixture
def finalisation_recording(
    postgres_session_factory,
    monkeypatch,
    tmp_path,
):
    """Create one isolated recording with one mapped parking bay."""

    monkeypatch.setattr(
        service,
        "SessionLocal",
        postgres_session_factory,
    )

    organisation_id = uuid.uuid4()
    site_id = uuid.uuid4()
    camera_id = uuid.uuid4()
    recording_id = uuid.uuid4()
    bay_id = uuid.uuid4()
    token = uuid.uuid4()

    video_root = tmp_path / "videos"
    result_root = tmp_path / "results"
    checkpoint = tmp_path / "model.pt"

    video_root.mkdir()
    (video_root / f"{recording_id}.mp4").write_bytes(b"test-video")
    checkpoint.write_bytes(b"test-checkpoint")

    monkeypatch.setattr(service, "VIDEO_ROOT", video_root)
    monkeypatch.setattr(service, "RESULT_ROOT", result_root)
    monkeypatch.setenv(
        "PARKSIGHT_OCCUPANCY_CHECKPOINT",
        str(checkpoint),
    )

    class FakeHeartbeat:
        lost = False

        def __init__(self, **kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            pass

    monkeypatch.setattr(service, "LeaseHeartbeat", FakeHeartbeat)

    def fake_camera_configuration(db, camera_id_arg):
        assert camera_id_arg == camera_id

        camera = db.get(Camera, camera_id)
        bays = db.scalars(
            select(ParkingBay).where(
                ParkingBay.camera_id == camera_id
            )
        ).all()

        return camera, None, bays

    monkeypatch.setattr(
        service,
        "load_camera_configuration",
        fake_camera_configuration,
    )

    def fake_process_video(**kwargs):
        output_path = kwargs["output_path"]

        with output_path.open("w", newline="") as file:
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
                "timestamp_seconds": "0.0",
                "bay_id": "B01",
                "state": "empty",
                "occupied_probability": "0.1",
                "available": "True",
                "temporal_state": "empty",
                "temporal_available": "True",
            })

        return {
            "frames_processed": 1,
            "predictions_written": 1,
        }

    monkeypatch.setattr(
        service,
        "process_video",
        fake_process_video,
    )

    try:
        with postgres_session_factory.begin() as db:
            assert db.scalar(
                text("SELECT current_database()")
            ) == "parksight_test"

            db.add(Organisation(
                id=organisation_id,
                name="Pytest Finalisation Organisation",
            ))
            db.flush()

            db.add(ParkingSite(
                id=site_id,
                organisation_id=organisation_id,
                name="Pytest Finalisation Site",
                status="active",
            ))
            db.flush()

            db.add(Camera(
                id=camera_id,
                site_id=site_id,
                name="Pytest Finalisation Camera",
                status="active",
            ))
            db.flush()

            db.add(ParkingBay(
                id=bay_id,
                site_id=site_id,
                camera_id=camera_id,
                bay_code="B01",
                bay_type="standard",
                polygon=[
                    [0, 0],
                    [100, 0],
                    [100, 100],
                    [0, 100],
                ],
            ))

            db.add(VideoRecording(
                id=recording_id,
                camera_id=camera_id,
                original_filename="finalisation-test.mp4",
                storage_key=f"{recording_id}.mp4",
                file_size_bytes=1024,
                status="processing",
                processing_attempts=1,
                processing_token=token,
                lease_expires_at=(
                    datetime.now(timezone.utc)
                    + timedelta(minutes=10)
                ),
                processing_started_at=datetime.now(timezone.utc),
            ))

        yield {
            "organisation_id": organisation_id,
            "site_id": site_id,
            "camera_id": camera_id,
            "recording_id": recording_id,
            "bay_id": bay_id,
            "token": token,
        }

    finally:
        with postgres_session_factory.begin() as db:
            assert db.scalar(
                text("SELECT current_database()")
            ) == "parksight_test"

            for observation in db.scalars(
                select(OccupancyObservation).where(
                    OccupancyObservation.recording_id == recording_id
                )
            ).all():
                db.delete(observation)

            db.flush()

            for model, entity_id in [
                (VideoRecording, recording_id),
                (ParkingBay, bay_id),
                (Camera, camera_id),
                (ParkingSite, site_id),
                (Organisation, organisation_id),
            ]:
                entity = db.get(model, entity_id)
                if entity is not None:
                    db.delete(entity)
                    db.flush()


def test_successful_finalisation_commits_observations(
    finalisation_recording,
    postgres_session_factory,
):
    data = finalisation_recording

    result = service.process_recording(
        organisation_id=data["organisation_id"],
        site_id=data["site_id"],
        camera_id=data["camera_id"],
        recording_id=data["recording_id"],
        claimed_token=data["token"],
    )

    assert result["status"] == "completed"
    assert result["import"]["created"] == 1
    assert result["import"]["skipped"] == 0

    with postgres_session_factory() as db:
        recording = db.get(
            VideoRecording,
            data["recording_id"],
        )

        observations = db.scalars(
            select(OccupancyObservation).where(
                OccupancyObservation.recording_id
                == data["recording_id"]
            )
        ).all()

        assert recording.status == "completed"
        assert recording.processing_attempts == 1
        assert recording.processing_token is None
        assert recording.lease_expires_at is None
        assert recording.processing_finished_at is not None
        assert recording.last_processing_error is None

        assert len(observations) == 1
        assert observations[0].bay_id == data["bay_id"]
        assert observations[0].raw_state == "empty"
        assert observations[0].temporal_state == "empty"
        assert observations[0].occupied_probability == pytest.approx(0.1)


def test_finalisation_failure_rolls_back_observations(
    finalisation_recording,
    postgres_session_factory,
    monkeypatch,
):
    """Staged observations must roll back if finalisation validation fails."""

    data = finalisation_recording
    real_import = service.import_observations

    def inconsistent_import(*args, **kwargs):
        result = real_import(*args, **kwargs)

        assert result["created"] == 1

        # Simulate a consistency failure after staging the observation.
        return {
            **result,
            "total": result["total"] + 1,
        }

    monkeypatch.setattr(
        service,
        "import_observations",
        inconsistent_import,
    )

    with pytest.raises(
        service.RecordingProcessingError,
        match="Imported observations do not match processor metrics",
    ):
        service.process_recording(
            organisation_id=data["organisation_id"],
            site_id=data["site_id"],
            camera_id=data["camera_id"],
            recording_id=data["recording_id"],
            claimed_token=data["token"],
        )

    with postgres_session_factory() as db:
        recording = db.get(
            VideoRecording,
            data["recording_id"],
        )

        observations = db.scalars(
            select(OccupancyObservation).where(
                OccupancyObservation.recording_id
                == data["recording_id"]
            )
        ).all()

        assert observations == []

        assert recording.status == "failed"
        assert recording.processing_attempts == 1
        assert recording.processing_token is None
        assert recording.lease_expires_at is None
        assert recording.processing_finished_at is not None

        assert (
            "Imported observations do not match processor metrics"
            in recording.last_processing_error
        )


def test_stale_worker_cannot_finalise_after_ownership_changes(
    finalisation_recording,
    postgres_session_factory,
    monkeypatch,
):
    """A worker whose token was replaced must not finalise a recording."""

    data = finalisation_recording
    replacement_token = uuid.uuid4()

    real_validate = service.validate_predictions

    def replace_ownership_after_inference(*args, **kwargs):
        result = real_validate(*args, **kwargs)

        with postgres_session_factory.begin() as db:
            recording = db.get(
                VideoRecording,
                data["recording_id"],
            )

            assert recording.processing_token == data["token"]

            recording.processing_token = replacement_token
            recording.processing_attempts += 1
            recording.lease_expires_at = (
                datetime.now(timezone.utc)
                + timedelta(minutes=10)
            )

        return result

    monkeypatch.setattr(
        service,
        "validate_predictions",
        replace_ownership_after_inference,
    )

    with pytest.raises(
        service.RecordingConflict,
        match="Recording processing claim is no longer valid",
    ):
        service.process_recording(
            organisation_id=data["organisation_id"],
            site_id=data["site_id"],
            camera_id=data["camera_id"],
            recording_id=data["recording_id"],
            claimed_token=data["token"],
        )

    with postgres_session_factory() as db:
        recording = db.get(
            VideoRecording,
            data["recording_id"],
        )

        observations = db.scalars(
            select(OccupancyObservation).where(
                OccupancyObservation.recording_id
                == data["recording_id"]
            )
        ).all()

        assert observations == []
        assert recording.status == "processing"
        assert recording.processing_token == replacement_token
        assert recording.processing_attempts == 2
        assert recording.lease_expires_at is not None
        assert recording.processing_finished_at is None
        assert recording.last_processing_error is None


def test_expired_lease_prevents_finalisation(
    finalisation_recording,
    postgres_session_factory,
    monkeypatch,
):
    """An expired lease must prevent observation import and completion."""

    data = finalisation_recording
    real_validate = service.validate_predictions

    def expire_lease_after_inference(*args, **kwargs):
        result = real_validate(*args, **kwargs)

        with postgres_session_factory.begin() as db:
            recording = db.get(
                VideoRecording,
                data["recording_id"],
            )

            assert recording.processing_token == data["token"]

            recording.lease_expires_at = (
                datetime.now(timezone.utc)
                - timedelta(seconds=5)
            )

        return result

    monkeypatch.setattr(
        service,
        "validate_predictions",
        expire_lease_after_inference,
    )

    with pytest.raises(
        service.RecordingConflict,
        match="Recording processing claim is no longer valid",
    ):
        service.process_recording(
            organisation_id=data["organisation_id"],
            site_id=data["site_id"],
            camera_id=data["camera_id"],
            recording_id=data["recording_id"],
            claimed_token=data["token"],
        )

    with postgres_session_factory() as db:
        recording = db.get(
            VideoRecording,
            data["recording_id"],
        )

        observations = db.scalars(
            select(OccupancyObservation).where(
                OccupancyObservation.recording_id
                == data["recording_id"]
            )
        ).all()

        assert observations == []

        assert recording.status == "processing"
        assert recording.processing_token == data["token"]
        assert recording.processing_attempts == 1
        assert recording.lease_expires_at < datetime.now(timezone.utc)
        assert recording.processing_finished_at is None
        assert recording.last_processing_error is None
