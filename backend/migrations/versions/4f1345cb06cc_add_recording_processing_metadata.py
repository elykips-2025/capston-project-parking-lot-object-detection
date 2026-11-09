"""add recording processing metadata

Revision ID: 4f1345cb06cc
Revises: 6fe46f0c5c16
Create Date: 2026-11-09 00:13:42.966568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f1345cb06cc'
down_revision: Union[str, Sequence[str], None] = '6fe46f0c5c16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "video_recordings",
        sa.Column(
            "processing_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "video_recordings",
        sa.Column(
            "processing_finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "video_recordings",
        sa.Column(
            "processing_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "video_recordings",
        sa.Column(
            "last_processing_error",
            sa.Text(),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_video_recordings_processing_attempts",
        "video_recordings",
        "processing_attempts >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_video_recordings_processing_attempts",
        "video_recordings",
        type_="check",
    )
    op.drop_column("video_recordings", "last_processing_error")
    op.drop_column("video_recordings", "processing_attempts")
    op.drop_column("video_recordings", "processing_finished_at")
    op.drop_column("video_recordings", "processing_started_at")
