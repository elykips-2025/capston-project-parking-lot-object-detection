import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.core.database import Base
from app.core.dependencies import get_db
from app.main import app
from app.models import Organisation
from app.models.organisation_membership import OrganisationMembership
from app.models.user import User


@pytest.fixture
def organisation_api():
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

    user_a = User(
        id=uuid.uuid4(),
        email="owner-a@example.test",
        password_hash="test-only",
        is_active=True,
    )
    user_b = User(
        id=uuid.uuid4(),
        email="owner-b@example.test",
        password_hash="test-only",
        is_active=True,
    )

    with Session.begin() as db:
        db.add_all([user_a, user_b])

    def override_db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db

    try:
        with TestClient(app) as client:
            yield client, Session, user_a, user_b
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def authenticate(user):
    app.dependency_overrides[get_current_user] = lambda: user


def test_unauthenticated_requests_are_rejected(organisation_api):
    client, _, _, _ = organisation_api

    assert client.get("/api/v1/organisations").status_code == 401
    assert client.post(
        "/api/v1/organisations",
        json={"name": "Test Organisation"},
    ).status_code == 401


def test_creation_assigns_owner_membership(organisation_api):
    client, Session, user_a, _ = organisation_api
    authenticate(user_a)

    response = client.post(
        "/api/v1/organisations",
        json={"name": "  ParkSight Operations  "},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "ParkSight Operations"

    organisation_id = uuid.UUID(response.json()["id"])

    with Session() as db:
        membership = db.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == organisation_id,
                OrganisationMembership.user_id == user_a.id,
            )
        )
        assert membership is not None
        assert membership.role == "owner"


def test_users_only_list_their_organisations(organisation_api):
    client, _, user_a, user_b = organisation_api

    authenticate(user_a)
    created = client.post(
        "/api/v1/organisations",
        json={"name": "Private Organisation"},
    )
    assert created.status_code == 201

    authenticate(user_b)
    response = client.get("/api/v1/organisations")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("name", ["  ", "A"])
def test_invalid_organisation_names_are_rejected(
    organisation_api,
    name,
):
    client, _, user_a, _ = organisation_api
    authenticate(user_a)

    response = client.post(
        "/api/v1/organisations",
        json={"name": name},
    )

    assert response.status_code == 422


def test_other_user_cannot_access_organisation_sites(organisation_api):
    client, _, user_a, user_b = organisation_api

    authenticate(user_a)
    created = client.post(
        "/api/v1/organisations",
        json={"name": "Restricted Organisation"},
    )
    assert created.status_code == 201

    organisation_id = created.json()["id"]

    authenticate(user_b)
    response = client.get(
        f"/api/v1/organisations/{organisation_id}/sites"
    )

    assert response.status_code == 404
