from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


@pytest.fixture(scope="session")
def postgres_test_engine():
    """Connect exclusively to the ParkSight integration-test database."""

    dev_url = make_url(settings.database_url)

    if dev_url.database != "parksight":
        pytest.fail(
            "Unsafe configuration: expected parksight development database"
        )

    test_url = dev_url.set(database="parksight_test")

    engine = create_engine(
        test_url,
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as connection:
            actual_database = connection.scalar(
                text("SELECT current_database()")
            )

            if actual_database != "parksight_test":
                pytest.fail(
                    f"Unsafe test database: {actual_database}"
                )

            revision = connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )

            alembic_config = Config(
                str(Path(__file__).resolve().parents[1] / "alembic.ini")
            )

            script = ScriptDirectory.from_config(alembic_config)
            expected_revision = script.get_current_head()

            if revision != expected_revision:
                pytest.fail(
                    f"Unexpected test schema revision: {revision}. "
                    f"Expected: {expected_revision}"
                )

        yield engine

    finally:
        engine.dispose()


@pytest.fixture
def postgres_session_factory(postgres_test_engine):
    """Provide independent PostgreSQL sessions for concurrency tests."""

    return sessionmaker(
        bind=postgres_test_engine,
        autoflush=False,
        expire_on_commit=False,
    )
