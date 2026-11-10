
import io
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.core.database import Base
from app.core.dependencies import get_db
from app.main import app
from app.models import Camera, Organisation, ParkingSite
from app.models.organisation_membership import OrganisationMembership
from app.models.user import User


@pytest.fixture
def camera_api(tmp_path, monkeypatch):
    import app.api.cameras as cameras_module

    # Redirect the endpoint's backend root to temporary storage.
    # This requires cameras.py to expose BACKEND_ROOT.
    monkeypatch.setattr(
        cameras_module,
        "BACKEND_ROOT",
        tmp_path,
    )

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    user = User(
        id=uuid.uuid4(),
        email="camera-owner@example.test",
        password_hash="test-only",
        is_active=True,
    )

    organisation = Organisation(
        id=uuid.uuid4(),
        name="Camera Test Organisation",
    )

    site = ParkingSite(
        id=uuid.uuid4(),
        organisation_id=organisation.id,
        name="Camera Test Site",
        status="active",
    )

    camera = Camera(
        id=uuid.uuid4(),
        site_id=site.id,
        name="Camera 001",
        status="active",
    )

    membership = OrganisationMembership(
        organisation_id=organisation.id,
        user_id=user.id,
        role="owner",
    )

    with Session.begin() as db:
        db.add_all([
            user,
            organisation,
            membership,
            site,
            camera,
        ])

    def override_db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        with TestClient(app) as client:
            yield client, Session, organisation, site, camera
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_owner_can_upload_reference_image(camera_api):
    client, Session, organisation, site, camera = camera_api

    image_buffer = io.BytesIO()
    Image.new("RGB", (640, 480)).save(
        image_buffer,
        format="JPEG",
    )

    url = (
        f"/api/v1/organisations/{organisation.id}"
        f"/sites/{site.id}/cameras/{camera.id}/reference-image"
    )

    response = client.put(
        url,
        files={
            "file": (
                "reference.jpg",
                image_buffer.getvalue(),
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["width"] == 640
    assert response.json()["height"] == 480

    with Session() as db:
        saved_camera = db.scalar(
            select(Camera).where(Camera.id == camera.id)
        )

        assert saved_camera.reference_image_storage_key
        assert saved_camera.reference_image_storage_key.startswith(
            "storage/camera-references/"
        )


def test_unauthenticated_upload_is_rejected(camera_api):
    client, _, organisation, site, camera = camera_api

    app.dependency_overrides.pop(get_current_user, None)

    url = (
        f"/api/v1/organisations/{organisation.id}"
        f"/sites/{site.id}/cameras/{camera.id}/reference-image"
    )

    response = client.put(
        url,
        files={"file": ("reference.jpg", b"invalid", "image/jpeg")},
    )

    assert response.status_code == 401


def test_cross_organisation_upload_is_rejected(camera_api):
    client, _, organisation, site, camera = camera_api

    url = (
        f"/api/v1/organisations/{uuid.uuid4()}"
        f"/sites/{site.id}/cameras/{camera.id}/reference-image"
    )

    response = client.put(
        url,
        files={"file": ("reference.jpg", b"invalid", "image/jpeg")},
    )

    assert response.status_code == 404


def test_invalid_image_content_is_rejected(camera_api):
    client, _, organisation, site, camera = camera_api

    url = (
        f"/api/v1/organisations/{organisation.id}"
        f"/sites/{site.id}/cameras/{camera.id}/reference-image"
    )

    response = client.put(
        url,
        files={
            "file": (
                "reference.jpg",
                b"This is not a JPEG image",
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 422

def test_other_tenant_cannot_upload_reference_image(camera_api):
    client, Session, organisation, site, camera = camera_api

    other_user = User(
        id=uuid.uuid4(),
        email="other-tenant@example.test",
        password_hash="test-only",
        is_active=True,
    )

    other_organisation = Organisation(
        id=uuid.uuid4(),
        name="Other Tenant Organisation",
    )

    with Session.begin() as db:
        db.add_all([
            other_user,
            other_organisation,
            OrganisationMembership(
                organisation_id=other_organisation.id,
                user_id=other_user.id,
                role="owner",
            ),
        ])

    app.dependency_overrides[get_current_user] = lambda: other_user

    image_buffer = io.BytesIO()
    Image.new("RGB", (640, 480)).save(
        image_buffer,
        format="JPEG",
    )

    url = (
        f"/api/v1/organisations/{organisation.id}"
        f"/sites/{site.id}/cameras/{camera.id}/reference-image"
    )

    response = client.put(
        url,
        files={
            "file": (
                "reference.jpg",
                image_buffer.getvalue(),
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 404

    with Session() as db:
        saved_camera = db.get(Camera, camera.id)
        assert saved_camera.reference_image_storage_key is None


def test_oversized_reference_image_is_rejected(camera_api):
    client, Session, organisation, site, camera = camera_api

    url = (
        f"/api/v1/organisations/{organisation.id}"
        f"/sites/{site.id}/cameras/{camera.id}/reference-image"
    )

    response = client.put(
        url,
        files={
            "file": (
                "oversized.jpg",
                b"x" * (10 * 1024 * 1024 + 1),
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 413

    with Session() as db:
        saved_camera = db.get(Camera, camera.id)
        assert saved_camera.reference_image_storage_key is None


def test_reference_image_replacement_blocked_when_bays_exist(camera_api):
    from app.models import ParkingBay

    client, Session, organisation, site, camera = camera_api

    with Session.begin() as db:
        db.add(
            ParkingBay(
                site_id=site.id,
                camera_id=camera.id,
                bay_code="A01",
                bay_type="standard",
                polygon=[
                    {"x": 10, "y": 10},
                    {"x": 100, "y": 10},
                    {"x": 100, "y": 100},
                    {"x": 10, "y": 100},
                ],
            )
        )

    image_buffer = io.BytesIO()
    Image.new("RGB", (640, 480)).save(
        image_buffer,
        format="JPEG",
    )

    url = (
        f"/api/v1/organisations/{organisation.id}"
        f"/sites/{site.id}/cameras/{camera.id}/reference-image"
    )

    response = client.put(
        url,
        files={
            "file": (
                "replacement.jpg",
                image_buffer.getvalue(),
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 409

    with Session() as db:
        saved_camera = db.get(Camera, camera.id)
        assert saved_camera.reference_image_storage_key is None
