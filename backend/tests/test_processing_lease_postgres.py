import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from sqlalchemy import select, text

from app.models import (
    Camera,
    Organisation,
    ParkingSite,
    VideoRecording,
)
from worker import processing_lease


@pytest.fixture
def test_recording(postgres_session_factory, monkeypatch):
    """Create an isolated recording and clean up its parent hierarchy."""

    monkeypatch.setattr(
        processing_lease,
        "SessionLocal",
        postgres_session_factory,
    )

    organisation_id = uuid.uuid4()
    site_id = uuid.uuid4()
    camera_id = uuid.uuid4()
    recording_id = uuid.uuid4()
    original_token = uuid.uuid4()

    expired_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    try:
        with postgres_session_factory.begin() as db:
            assert db.scalar(
                text("SELECT current_database()")
            ) == "parksight_test"

            db.add(
                Organisation(
                    id=organisation_id,
                    name="Pytest Lease Recovery Organisation",
                )
            )
            db.flush()

            db.add(
                ParkingSite(
                    id=site_id,
                    organisation_id=organisation_id,
                    name="Pytest Parking Site",
                    status="active",
                )
            )
            db.flush()

            db.add(
                Camera(
                    id=camera_id,
                    site_id=site_id,
                    name="Pytest Camera",
                    status="active",
                )
            )
            db.flush()

            db.add(
                VideoRecording(
                    id=recording_id,
                    camera_id=camera_id,
                    original_filename="pytest-recovery.mp4",
                    storage_key=f"pytest/{recording_id}.mp4",
                    file_size_bytes=1024,
                    status="processing",
                    processing_attempts=1,
                    processing_token=original_token,
                    lease_expires_at=expired_at,
                    processing_started_at=expired_at,
                )
            )

        yield {
            "recording_id": recording_id,
            "original_token": original_token,
        }

    finally:
        with postgres_session_factory.begin() as db:
            assert db.scalar(
                text("SELECT current_database()")
            ) == "parksight_test"

            recording = db.get(VideoRecording, recording_id)
            if recording is not None:
                db.delete(recording)
                db.flush()

            camera = db.get(Camera, camera_id)
            if camera is not None:
                db.delete(camera)
                db.flush()

            site = db.get(ParkingSite, site_id)
            if site is not None:
                db.delete(site)
                db.flush()

            organisation = db.get(Organisation, organisation_id)
            if organisation is not None:
                db.delete(organisation)


def test_concurrent_recovery_has_exactly_one_winner(
    test_recording,
    postgres_session_factory,
):
    """Two concurrent workers cannot reclaim the same expired lease."""

    recording_id = test_recording["recording_id"]
    original_token = test_recording["original_token"]

    barrier = Barrier(2)

    def attempt_recovery():
        barrier.wait(timeout=10)
        return processing_lease.reclaim_expired_recording(
            recording_id,
            max_attempts=3,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(attempt_recovery)
            for _ in range(2)
        ]

        results = [
            future.result(timeout=15)
            for future in futures
        ]

    winners = [token for token in results if token is not None]

    assert len(winners) == 1
    assert results.count(None) == 1
    assert winners[0] != original_token

    with postgres_session_factory() as db:
        recording = db.scalar(
            select(VideoRecording).where(
                VideoRecording.id == recording_id
            )
        )

        assert recording is not None
        assert recording.status == "processing"
        assert recording.processing_attempts == 2
        assert recording.processing_token == winners[0]
        assert recording.lease_expires_at > datetime.now(timezone.utc)


def test_current_owner_can_renew_lease(
    test_recording,
    postgres_session_factory,
):
    """A valid owner can extend an unexpired lease."""

    recording_id = test_recording["recording_id"]
    token = test_recording["original_token"]

    with postgres_session_factory.begin() as db:
        recording = db.get(VideoRecording, recording_id)
        recording.lease_expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=30)
        )

    with postgres_session_factory() as db:
        previous_expiry = db.get(
            VideoRecording, recording_id
        ).lease_expires_at

    assert processing_lease.renew_lease(recording_id, token) is True

    with postgres_session_factory() as db:
        recording = db.get(VideoRecording, recording_id)

        assert recording.processing_token == token
        assert recording.lease_expires_at > previous_expiry
        assert recording.processing_attempts == 1


def test_invalid_token_cannot_renew_lease(
    test_recording,
    postgres_session_factory,
):
    """A worker without the ownership token cannot extend a lease."""

    recording_id = test_recording["recording_id"]

    with postgres_session_factory.begin() as db:
        recording = db.get(VideoRecording, recording_id)
        recording.lease_expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=60)
        )

    invalid_token = uuid.uuid4()

    assert (
        processing_lease.renew_lease(
            recording_id, invalid_token
        )
        is False
    )

    with postgres_session_factory() as db:
        recording = db.get(VideoRecording, recording_id)
        assert recording.processing_token != invalid_token
        assert recording.processing_attempts == 1


def test_expired_lease_cannot_be_renewed(
    test_recording,
    postgres_session_factory,
):
    """Even the original owner cannot renew an expired lease."""

    recording_id = test_recording["recording_id"]
    token = test_recording["original_token"]

    assert processing_lease.renew_lease(recording_id, token) is False

    with postgres_session_factory() as db:
        recording = db.get(VideoRecording, recording_id)
        assert recording.processing_token == token
        assert recording.processing_attempts == 1


def test_stale_worker_cannot_renew_after_recovery(
    test_recording,
    postgres_session_factory,
):
    """A previous owner loses renewal rights after another claim."""

    recording_id = test_recording["recording_id"]
    stale_token = test_recording["original_token"]

    new_token = processing_lease.reclaim_expired_recording(
        recording_id,
        max_attempts=3,
    )

    assert new_token is not None
    assert new_token != stale_token

    assert (
        processing_lease.renew_lease(
            recording_id, stale_token
        )
        is False
    )

    assert (
        processing_lease.renew_lease(
            recording_id, new_token
        )
        is True
    )

    with postgres_session_factory() as db:
        recording = db.get(VideoRecording, recording_id)

        assert recording.processing_token == new_token
        assert recording.processing_attempts == 2
        assert recording.status == "processing"


def test_exhausted_recording_cannot_be_reclaimed(
    test_recording,
    postgres_session_factory,
):
    """A recording at the retry limit cannot acquire another lease."""

    recording_id = test_recording["recording_id"]
    original_token = test_recording["original_token"]

    with postgres_session_factory.begin() as db:
        recording = db.get(VideoRecording, recording_id)

        recording.processing_attempts = 3

    result = processing_lease.reclaim_expired_recording(
        recording_id,
        max_attempts=3,
    )

    assert result is None

    with postgres_session_factory() as db:
        recording = db.get(VideoRecording, recording_id)

        assert recording.status == "processing"
        assert recording.processing_attempts == 3
        assert recording.processing_token == original_token
        assert recording.lease_expires_at < datetime.now(
            timezone.utc
        )


def test_exhausted_recording_transitions_to_failed(
    test_recording,
    postgres_session_factory,
    monkeypatch,
):
    """The worker marks an expired, exhausted recording as failed."""

    from worker import recording_worker

    monkeypatch.setattr(
        recording_worker,
        "SessionLocal",
        postgres_session_factory,
    )

    recording_id = test_recording["recording_id"]

    with postgres_session_factory.begin() as db:
        recording = db.get(VideoRecording, recording_id)
        recording.processing_attempts = 3

    recording_worker.fail_exhausted_recordings()

    with postgres_session_factory() as db:
        recording = db.get(VideoRecording, recording_id)

        assert recording.status == "failed"
        assert recording.processing_attempts == 3
        assert recording.processing_token is None
        assert recording.lease_expires_at is None
        assert recording.processing_finished_at is not None
        assert recording.last_processing_error
        assert "maximum attempts exhausted" in (
            recording.last_processing_error
        )

    # The failed recording must not be eligible for expired-lease recovery.
    assert (
        processing_lease.reclaim_expired_recording(
            recording_id,
            max_attempts=3,
        )
        is None
    )


def test_finalisation_blocks_concurrent_recovery(
    test_recording,
    postgres_session_factory,
):
    """Recovery blocks on PostgreSQL row lock and loses after commit."""

    import time
    from threading import Event, Lock

    from sqlalchemy import event, text

    recording_id = test_recording["recording_id"]
    original_token = test_recording["original_token"]

    engine = postgres_session_factory.kw["bind"]

    row_locked = Event()
    recovery_update_started = Event()
    release_finalisation = Event()

    backend = {}
    backend_lock = Lock()

    def observe_recovery_update(
        conn, cursor, statement, parameters, context, executemany
    ):
        if (
            statement.lstrip().upper().startswith("UPDATE")
            and "video_recordings" in statement
            and "lease_expires_at" in statement
        ):
            with backend_lock:
                backend["recovery_pid"] = conn.connection.driver_connection.info.backend_pid

            recovery_update_started.set()

    def finalise_recording():
        with postgres_session_factory.begin() as db:
            recording = db.scalar(
                select(VideoRecording)
                .where(VideoRecording.id == recording_id)
                .with_for_update()
            )

            assert recording is not None
            assert recording.processing_token == original_token

            backend["finaliser_pid"] = db.scalar(
                text("SELECT pg_backend_pid()")
            )

            row_locked.set()

            if not release_finalisation.wait(timeout=15):
                raise TimeoutError("Finalisation release timed out")

            recording.status = "completed"
            recording.processing_finished_at = datetime.now(
                timezone.utc
            )
            recording.processing_token = None
            recording.lease_expires_at = None

    def attempt_recovery():
        assert row_locked.wait(timeout=10)

        return processing_lease.reclaim_expired_recording(
            recording_id,
            max_attempts=3,
        )

    event.listen(
        engine,
        "before_cursor_execute",
        observe_recovery_update,
    )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            finalisation_future = executor.submit(finalise_recording)

            assert row_locked.wait(timeout=10)

            recovery_future = executor.submit(attempt_recovery)

            try:
                assert recovery_update_started.wait(timeout=10)

                deadline = time.monotonic() + 10
                blocked = False

                while time.monotonic() < deadline:
                    with postgres_session_factory() as monitor:
                        blockers = monitor.scalar(
                            text("SELECT pg_blocking_pids(:pid)"),
                            {"pid": backend["recovery_pid"]},
                        )

                    if backend["finaliser_pid"] in blockers:
                        blocked = True
                        break

                    time.sleep(0.05)

                assert blocked, (
                    "PostgreSQL did not report recovery blocked "
                    "by the finalisation transaction"
                )

            finally:
                release_finalisation.set()

            finalisation_future.result(timeout=15)
            recovery_token = recovery_future.result(timeout=15)

        assert recovery_token is None

        with postgres_session_factory() as db:
            recording = db.get(VideoRecording, recording_id)

            assert recording.status == "completed"
            assert recording.processing_attempts == 1
            assert recording.processing_token is None
            assert recording.lease_expires_at is None
            assert recording.processing_finished_at is not None

    finally:
        event.remove(
            engine,
            "before_cursor_execute",
            observe_recovery_update,
        )
