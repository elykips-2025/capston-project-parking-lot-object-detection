
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OccupancyObservation(Base):
    __tablename__ = "occupancy_observations"

    __table_args__ = (
        CheckConstraint(
            "raw_state IN ('occupied', 'empty', 'unknown')",
            name="ck_occupancy_raw_state",
        ),
        CheckConstraint(
            "temporal_state IN ('occupied', 'empty', 'unknown')",
            name="ck_occupancy_temporal_state",
        ),
        CheckConstraint(
            "occupied_probability >= 0 AND occupied_probability <= 1",
            name="ck_occupancy_probability",
        ),
        CheckConstraint(
            "timestamp_seconds >= 0",
            name="ck_occupancy_timestamp",
        ),
        UniqueConstraint(
            "recording_id",
            "bay_id",
            "timestamp_seconds",
            name="uq_occupancy_recording_bay_timestamp",
        ),
        Index(
            "ix_occupancy_bay_recording_timestamp",
            "bay_id",
            "recording_id",
            "timestamp_seconds",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    recording_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_recordings.id"),
        nullable=False,
        index=True,
    )

    bay_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parking_bays.id"),
        nullable=False,
        index=True,
    )

    timestamp_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    raw_state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    temporal_state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    occupied_probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
