import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import update, or_

from app.core.database import SessionLocal
from app.models import VideoRecording


LEASE_SECONDS = 120


def utcnow():
    return datetime.now(timezone.utc)


def claim_recording(recording_id, *, allow_retry=False):
    """
    Atomically claim an uploaded recording.

    Returns a unique processing token or None when the recording
    is not eligible.
    """
    token = uuid.uuid4()
    now = utcnow()

    eligible = ["uploaded"]
    if allow_retry:
        eligible.append("failed")

    with SessionLocal.begin() as db:
        claimed = db.execute(
            update(VideoRecording)
            .where(
                VideoRecording.id == recording_id,
                VideoRecording.status.in_(eligible),
            )
            .values(
                status="processing",
                processing_token=token,
                lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
                processing_started_at=now,
                processing_finished_at=None,
                processing_attempts=VideoRecording.processing_attempts + 1,
                last_processing_error=None,
            )
            .returning(VideoRecording.id)
        ).scalar_one_or_none()

    return token if claimed else None


def renew_lease(recording_id, token):
    """Extend the lease only if this worker still owns it."""
    now = utcnow()

    with SessionLocal.begin() as db:
        updated = db.execute(
            update(VideoRecording)
            .where(
                VideoRecording.id == recording_id,
                VideoRecording.status == "processing",
                VideoRecording.processing_token == token,
                VideoRecording.lease_expires_at > now,
            )
            .values(
                lease_expires_at=now + timedelta(seconds=LEASE_SECONDS)
            )
            .returning(VideoRecording.id)
        ).scalar_one_or_none()

    return updated is not None



def reclaim_expired_recording(recording_id, *, max_attempts=3):
    """
    Atomically reclaim an expired recording with no observations.

    Returns a new token or None when ineligible.
    """
    from sqlalchemy import exists, select
    from app.models import OccupancyObservation

    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")

    token = uuid.uuid4()
    now = utcnow()

    observations_exist = (
        select(OccupancyObservation.id)
        .where(OccupancyObservation.recording_id == recording_id)
        .exists()
    )

    with SessionLocal.begin() as db:
        claimed = db.execute(
            update(VideoRecording)
            .where(
                VideoRecording.id == recording_id,
                VideoRecording.status == "processing",
                VideoRecording.lease_expires_at.is_not(None),
                VideoRecording.lease_expires_at <= now,
                VideoRecording.processing_attempts < max_attempts,
                ~observations_exist,
            )
            .values(
                processing_token=token,
                lease_expires_at=now + timedelta(
                    seconds=LEASE_SECONDS
                ),
                processing_started_at=now,
                processing_finished_at=None,
                processing_attempts=(
                    VideoRecording.processing_attempts + 1
                ),
                last_processing_error=None,
            )
            .returning(VideoRecording.id)
        ).scalar_one_or_none()

    return token if claimed else None
