import csv
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy import select, update

from app.core.database import SessionLocal
from app.models import Camera, ParkingSite, VideoRecording
from worker.import_occupancy_observations import (
    EXPECTED_COLUMNS,
    import_observations,
)
from worker.inference.camera_configuration import (
    BACKEND_ROOT,
    load_camera_configuration,
)
from worker.inference.video_processor import process_video
from worker.processing_lease import LEASE_SECONDS
from worker.lease_heartbeat import LeaseHeartbeat


logger = logging.getLogger(__name__)

VIDEO_ROOT = BACKEND_ROOT / "storage" / "videos"
RESULT_ROOT = BACKEND_ROOT / "storage" / "processing"
DEFAULT_CHECKPOINT = (
    BACKEND_ROOT
    / "runs/occupancy/mobilenetv3_pilot/best.pt"
)


class RecordingProcessingError(RuntimeError):
    pass


class RecordingConflict(RecordingProcessingError):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def validate_predictions(csv_path, metrics, expected_bays):
    """Validate complete processor output before database import."""
    if metrics["frames_processed"] <= 0:
        raise RecordingProcessingError("No processed frames")

    expected = metrics["frames_processed"] * expected_bays

    if metrics["predictions_written"] != expected:
        raise RecordingProcessingError(
            "Processor prediction count mismatch"
        )

    snapshots = {}

    with csv_path.open(newline="") as file:
        reader = csv.DictReader(file)

        if not EXPECTED_COLUMNS.issubset(reader.fieldnames or []):
            raise RecordingProcessingError(
                "Prediction CSV missing required columns"
            )

        count = 0

        for row in reader:
            count += 1
            timestamp = row["timestamp_seconds"]
            bay_code = row["bay_id"]
            snapshots.setdefault(timestamp, []).append(bay_code)

    if count != expected:
        raise RecordingProcessingError(
            f"Incomplete output: expected {expected}, got {count}"
        )

    if len(snapshots) != metrics["frames_processed"]:
        raise RecordingProcessingError(
            "Unexpected number of prediction timestamps"
        )

    for timestamp, bay_codes in snapshots.items():
        if (
            len(bay_codes) != expected_bays
            or len(set(bay_codes)) != expected_bays
        ):
            raise RecordingProcessingError(
                f"Incomplete snapshot at {timestamp}"
            )

    return count


def process_recording(
    organisation_id: uuid.UUID,
    site_id: uuid.UUID,
    camera_id: uuid.UUID,
    recording_id: uuid.UUID,
    *,
    retry: bool = False,
    claimed_token: uuid.UUID | None = None,
    target_fps: float = 1.0,
) -> dict:
    """Process one recording, using short database transactions."""

    if not 0 < target_fps <= 30:
        raise ValueError("target_fps must be between 0 and 30")

    attempt_claimed = False
    attempt_number = None
    processing_token = claimed_token or uuid.uuid4()
    heartbeat = None

    # Phase 1: validate ownership and atomically claim the recording.
    with SessionLocal.begin() as db:
        recording = db.scalar(
            select(VideoRecording)
            .join(Camera, VideoRecording.camera_id == Camera.id)
            .join(ParkingSite, Camera.site_id == ParkingSite.id)
            .where(
                VideoRecording.id == recording_id,
                VideoRecording.camera_id == camera_id,
                Camera.site_id == site_id,
                ParkingSite.organisation_id == organisation_id,
                Camera.status == "active",
                ParkingSite.status == "active",
            )
        )

        if recording is None:
            raise RecordingProcessingError(
                "Recording or active camera/site not found"
            )

        if claimed_token is None:
            allowed = ["uploaded"]
            if retry:
                allowed.append("failed")

            claimed_id = db.scalar(
                update(VideoRecording)
                .where(
                    VideoRecording.id == recording_id,
                    VideoRecording.status.in_(allowed),
                )
                .values(
                    status="processing",
                    processing_token=processing_token,
                    lease_expires_at=utcnow() + timedelta(
                        seconds=LEASE_SECONDS
                    ),
                    processing_started_at=utcnow(),
                    processing_finished_at=None,
                    processing_attempts=(
                        VideoRecording.processing_attempts + 1
                    ),
                    last_processing_error=None,
                )
                .returning(VideoRecording.id)
            )

            if claimed_id is None:
                raise RecordingConflict(
                    "Recording is not eligible for processing"
                )
        else:
            claimed_id = db.scalar(
                select(VideoRecording.id)
                .where(
                    VideoRecording.id == recording_id,
                    VideoRecording.status == "processing",
                    VideoRecording.processing_token == claimed_token,
                    VideoRecording.lease_expires_at > utcnow(),
                )
                .with_for_update()
            )

            if claimed_id is None:
                raise RecordingConflict(
                    "Recovered processing claim is invalid or expired"
                )

        storage_key = recording.storage_key
        attempt_number = db.scalar(
            select(VideoRecording.processing_attempts)
            .where(VideoRecording.id == recording_id)
        )
        attempt_claimed = True

    # Use a unique output per attempt to avoid stale CSV reuse.
    run_id = uuid.uuid4()
    output_path = RESULT_ROOT / str(recording_id) / f"{run_id}.csv"
    try:
        heartbeat = LeaseHeartbeat(
            recording_id=recording_id,
            token=processing_token,
            interval_seconds=30,
        )
        heartbeat.start()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if storage_key != f"{recording_id}.mp4":
            raise RecordingProcessingError(
                "Unexpected recording storage key"
            )

        video_path = VIDEO_ROOT / storage_key

        if not video_path.is_file():
            raise FileNotFoundError("Recording video file not found")

        checkpoint = Path(
            os.getenv(
                "PARKSIGHT_OCCUPANCY_CHECKPOINT",
                str(DEFAULT_CHECKPOINT),
            )
        )

        if not checkpoint.is_file():
            raise FileNotFoundError(
                "Occupancy checkpoint not found"
            )

        with SessionLocal() as db:
            camera, reference, bays = load_camera_configuration(
                db, camera_id
            )

        metrics = process_video(
            video_path=video_path,
            reference=reference,
            bays=bays,
            checkpoint_path=checkpoint,
            output_path=output_path,
            target_fps=target_fps,
        )

        validate_predictions(
            output_path,
            metrics,
            expected_bays=len(bays),
        )

        # Stop heartbeat before acquiring the final database row lock.
        heartbeat.stop()

        if heartbeat.lost:
            raise RecordingConflict(
                "Processing lease was lost during inference"
            )

        # Phase 2: import observations and complete atomically.
        with SessionLocal.begin() as db:
            recording = db.scalar(
                select(VideoRecording)
                .where(VideoRecording.id == recording_id)
                .with_for_update()
            )

            if (
                recording is None
                or recording.status != "processing"
                or recording.processing_attempts != attempt_number
                or recording.processing_token != processing_token
                or recording.lease_expires_at is None
                or recording.lease_expires_at <= utcnow()
            ):
                raise RecordingConflict(
                    "Recording processing claim is no longer valid"
                )

            # Recheck ownership and active configuration before import.
            active_camera = db.scalar(
                select(Camera)
                .join(ParkingSite, Camera.site_id == ParkingSite.id)
                .where(
                    Camera.id == camera_id,
                    Camera.site_id == site_id,
                    Camera.status == "active",
                    ParkingSite.id == site_id,
                    ParkingSite.organisation_id == organisation_id,
                    ParkingSite.status == "active",
                )
            )

            if active_camera is None:
                raise RecordingProcessingError(
                    "Camera or site became inactive"
                )

            result = import_observations(
                recording_id=recording_id,
                csv_path=output_path,
                db=db,
            )

            if (
                result["total"] != metrics["predictions_written"]
                or result["created"] != metrics["predictions_written"]
                or result["skipped"] != 0
                or result["timestamps"] != metrics["frames_processed"]
                or result["bays"] != len(bays)
            ):
                raise RecordingProcessingError(
                    "Imported observations do not match processor metrics"
                )

            recording.status = "completed"
            recording.processing_finished_at = utcnow()
            recording.processing_token = None
            recording.lease_expires_at = None
            recording.last_processing_error = None

        return {
            "recording_id": str(recording_id),
            "status": "completed",
            "processing": metrics,
            "import": result,
        }

    except Exception as exc:
        if heartbeat is not None:
            try:
                heartbeat.stop()
            except Exception:
                logger.exception(
                    "Failed to stop recording lease heartbeat"
                )

        logger.exception(
            "Recording processing failed: %s", recording_id
        )

        if attempt_claimed:
            # Separate transaction: preserve failure after import rollback.
            try:
                with SessionLocal.begin() as db:
                    db.execute(
                        update(VideoRecording)
                        .where(
                            VideoRecording.id == recording_id,
                            VideoRecording.status == "processing",
                            VideoRecording.processing_attempts
                            == attempt_number,
                            VideoRecording.processing_token
                            == processing_token,
                            VideoRecording.lease_expires_at
                            > utcnow(),
                        )
                        .values(
                            status="failed",
                            processing_token=None,
                            lease_expires_at=None,
                            processing_finished_at=utcnow(),
                            last_processing_error=(
                                f"{type(exc).__name__}: {exc}"
                            )[:4000],
                        )
                    )
            except Exception:
                logger.exception(
                    "Unable to persist failure diagnostics"
                )

        raise
