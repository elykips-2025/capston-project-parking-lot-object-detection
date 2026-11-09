import argparse
import logging
import signal
import time

from sqlalchemy import select, exists, update

from app.core.database import SessionLocal
from app.models import (
    VideoRecording,
    Camera,
    ParkingSite,
    OccupancyObservation,
)
from worker.recording_processing_service import (
    process_recording,
    RecordingConflict,
)
from worker.processing_lease import (
    reclaim_expired_recording,
    utcnow,
)


logger = logging.getLogger("parksight.recording_worker")
shutdown_requested = False


def request_shutdown(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    logger.info("Shutdown requested")


def next_recording():
    """Find the oldest eligible uploaded recording."""

    with SessionLocal() as db:
        return db.execute(
            select(
                VideoRecording.id,
                Camera.id.label("camera_id"),
                ParkingSite.id.label("site_id"),
                ParkingSite.organisation_id,
            )
            .join(Camera, VideoRecording.camera_id == Camera.id)
            .join(ParkingSite, Camera.site_id == ParkingSite.id)
            .where(
                VideoRecording.status == "uploaded",
                Camera.status == "active",
                ParkingSite.status == "active",
                ~exists().where(
                    OccupancyObservation.recording_id
                    == VideoRecording.id
                ),
            )
            .order_by(VideoRecording.created_at.asc())
            .limit(1)
        ).first()


MAX_ATTEMPTS = 3


def next_expired_recording():
    """Find an expired recording eligible for recovery."""

    with SessionLocal() as db:
        return db.execute(
            select(
                VideoRecording.id,
                Camera.id.label("camera_id"),
                ParkingSite.id.label("site_id"),
                ParkingSite.organisation_id,
            )
            .join(Camera, VideoRecording.camera_id == Camera.id)
            .join(ParkingSite, Camera.site_id == ParkingSite.id)
            .where(
                VideoRecording.status == "processing",
                VideoRecording.lease_expires_at.is_not(None),
                VideoRecording.lease_expires_at <= utcnow(),
                VideoRecording.processing_attempts < MAX_ATTEMPTS,
                Camera.status == "active",
                ParkingSite.status == "active",
                ~exists().where(
                    OccupancyObservation.recording_id
                    == VideoRecording.id
                ),
            )
            .order_by(VideoRecording.created_at.asc())
            .limit(1)
        ).first()


def fail_exhausted_recordings():
    """Mark expired recordings that exhausted retries as failed."""

    now = utcnow()

    with SessionLocal.begin() as db:
        result = db.execute(
            update(VideoRecording)
            .where(
                VideoRecording.status == "processing",
                VideoRecording.lease_expires_at.is_not(None),
                VideoRecording.lease_expires_at <= now,
                VideoRecording.processing_attempts >= MAX_ATTEMPTS,
                ~exists().where(
                    OccupancyObservation.recording_id
                    == VideoRecording.id
                ),
            )
            .values(
                status="failed",
                processing_finished_at=now,
                processing_token=None,
                lease_expires_at=None,
                last_processing_error=(
                    "Processing lease expired; "
                    "maximum attempts exhausted"
                ),
            )
            .returning(VideoRecording.id)
        )

        failed_ids = result.scalars().all()

    for recording_id in failed_ids:
        logger.error(
            "Recording %s exhausted processing attempts",
            recording_id,
        )


def run_worker(poll_interval):
    logger.info(
        "ParkSight recording worker started; polling every %ss",
        poll_interval,
    )

    while not shutdown_requested:
        try:
            fail_exhausted_recordings()

            job = next_recording()
            recovered = False
            token = None

            if job is None:
                job = next_expired_recording()
                recovered = job is not None

            if job is None:
                time.sleep(poll_interval)
                continue

            if recovered:
                token = reclaim_expired_recording(
                    job.id,
                    max_attempts=MAX_ATTEMPTS,
                )

                if token is None:
                    logger.info(
                        "Recovery claim lost for recording %s",
                        job.id,
                    )
                    continue

            logger.info(
                "%s recording %s",
                "Recovering" if recovered else "Processing",
                job.id,
            )

            result = process_recording(
                organisation_id=job.organisation_id,
                site_id=job.site_id,
                camera_id=job.camera_id,
                recording_id=job.id,
                claimed_token=token,
            )
            logger.info(
                "Completed recording %s: %s observations",
                job.id,
                result["import"]["created"],
            )

        except RecordingConflict:
            logger.info(
                "Recording %s claimed by another worker",
                job.id if job is not None else "unknown",
            )

        except Exception:
            logger.exception(
                "Worker iteration failed for recording %s",
                job.id if job is not None else "unknown",
            )
            time.sleep(poll_interval)

    logger.info("ParkSight recording worker stopped")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
    )
    args = parser.parse_args()

    if args.poll_interval <= 0:
        parser.error("--poll-interval must be positive")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    run_worker(args.poll_interval)


if __name__ == "__main__":
    main()
