"""add recording processing leases

Revision ID: eea4d40e4c3d
Revises: 4f1345cb06cc
Create Date: 2026-11-09 00:45:11.971407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eea4d40e4c3d'
down_revision: Union[str, Sequence[str], None] = '4f1345cb06cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "video_recordings",
        sa.Column(
            "processing_token",
            sa.UUID(),
            nullable=True,
        ),
    )
    op.add_column(
        "video_recordings",
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("video_recordings", "lease_expires_at")
    op.drop_column("video_recordings", "processing_token")
