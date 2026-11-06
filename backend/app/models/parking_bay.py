
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ParkingBay(Base):
    __tablename__ = "parking_bays"

    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "bay_code",
            name="uq_parking_bays_site_code",
        ),
        CheckConstraint(
            "bay_type IN ('standard', 'accessible', 'ev', 'reserved')",
            name="ck_parking_bays_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parking_sites.id"),
        nullable=False,
        index=True,
    )

    camera_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cameras.id"),
        nullable=False,
        index=True,
    )

    bay_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    bay_type: Mapped[str] = mapped_column(
        String(20),
        default="standard",
        nullable=False,
    )

    polygon: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
