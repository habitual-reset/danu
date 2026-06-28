"""voice hold jobs for async turn processing

Revision ID: 005
Revises: 004
Create Date: 2026-06-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_hold_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("call_sid", sa.String(length=64), nullable=False),
        sa.Column("speech_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("work_type", sa.String(length=32), nullable=False),
        sa.Column("estimated_seconds", sa.Integer(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_hold_jobs_tenant_id", "voice_hold_jobs", ["tenant_id"])
    op.create_index("ix_voice_hold_jobs_user_id", "voice_hold_jobs", ["user_id"])
    op.create_index("ix_voice_hold_jobs_conversation_id", "voice_hold_jobs", ["conversation_id"])
    op.create_index("ix_voice_hold_jobs_call_sid", "voice_hold_jobs", ["call_sid"])
    op.create_index("ix_voice_hold_jobs_status", "voice_hold_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("voice_hold_jobs")