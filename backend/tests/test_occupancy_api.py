import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.dependencies import get_db
from app.main import app
from app.models import (
    Camera,
    OccupancyObservation,
    Organisation,
    ParkingBay,
    ParkingSite,
    VideoRecording,
)


@pytest.fixture
def api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    organisation_id = uuid.uuid4()
    site_id = uuid.uuid4()
    camera_id = uuid.uuid4()
    recording_id = uuid.uuid4()

    with Session.begin() as db:
        db.add(Organisation(
            id=organisation_id,
            name="Integration Test Organisation",
        ))
        db.flush()

        db.add(ParkingSite(
            id=site_id,
            organisation_id=organisation_id,
            name="Integration Test Site",
        ))
        db.flush()

        db.add(Camera(
            id=camera_id,
            site_id=site_id,
            name="Test Camera",
        ))
        db.flush()

        db.add(VideoRecording(
            id=recording_id,
            camera_id=camera_id,
            original_filename="test.mp4",
            storage_key=f"tests/{recording_id}.mp4",
            file_size_bytes=1024,
        ))
        db.flush()

        bays = []
        for code in ("A01", "A02", "A03"):
            bay = ParkingBay(
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
            )
            db.add(bay)
            bays.append(bay)

        db.flush()

        snapshots = {
            0.0: ("unknown", "unknown", "unknown"),
            14.014: ("empty", "occupied", "unknown"),
            28.028: ("occupied", "occupied", "empty"),
        }

        for timestamp, states in snapshots.items():
            for bay, state in zip(bays, states):
                db.add(OccupancyObservation(
                    recording_id=recording_id,
                    bay_id=bay.id,
                    timestamp_seconds=timestamp,
                    raw_state=state,
                    temporal_state=state,
                    occupied_probability={
                        "empty": 0.05,
                        "occupied": 0.95,
                        "unknown": 0.5,
                    }[state],
                ))

    def override_db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db

    base_url = (
        f"/api/v1/organisations/{organisation_id}"
        f"/sites/{site_id}/occupancy"
    )

    try:
        with TestClient(app) as client:
            yield client, base_url, recording_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def get_snapshot(api, timestamp=None):
    client, base_url, recording_id = api
    params = {"recording_id": str(recording_id)}

    if timestamp is not None:
        params["timestamp_seconds"] = timestamp

    return client.get(base_url, params=params)


def test_default_returns_latest_snapshot(api):
    response = get_snapshot(api)

    assert response.status_code == 200
    data = response.json()

    assert data["timestamp_seconds"] == 28.028
    assert data["summary"] == {
        "total": 3,
        "available": 1,
        "occupied": 2,
        "unknown": 0,
    }


def test_historical_snapshot_returns_correct_bay_states(api):
    response = get_snapshot(api, 14.014)

    assert response.status_code == 200
    data = response.json()

    assert data["timestamp_seconds"] == 14.014
    assert {bay["code"]: bay["state"] for bay in data["bays"]} == {
        "A01": "empty",
        "A02": "occupied",
        "A03": "unknown",
    }

    assert data["summary"] == {
        "total": 3,
        "available": 1,
        "occupied": 1,
        "unknown": 1,
    }


def test_missing_timestamp_returns_404(api):
    response = get_snapshot(api, 10.0)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "timestamp",
    ["-1", "nan", "inf", "not-a-number"],
)
def test_invalid_timestamp_returns_422(api, timestamp):
    response = get_snapshot(api, timestamp)
    assert response.status_code == 422


@pytest.mark.parametrize("timestamp", [0.0, 14.014, 28.028])
def test_summary_matches_bay_states(api, timestamp):
    response = get_snapshot(api, timestamp)

    assert response.status_code == 200
    data = response.json()

    states = [bay["state"] for bay in data["bays"]]
    summary = data["summary"]

    assert summary["total"] == len(states)
    assert summary["available"] == states.count("empty")
    assert summary["occupied"] == states.count("occupied")
    assert summary["unknown"] == states.count("unknown")


def test_unknown_site_returns_404(api):
    client, base_url, recording_id = api
    unknown_site_url = base_url.replace(
        base_url.split("/sites/")[1].split("/")[0],
        str(uuid.uuid4()),
    )

    response = client.get(
        unknown_site_url,
        params={"recording_id": str(recording_id)},
    )

    assert response.status_code == 404
