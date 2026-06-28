"""memory graph entities and relations

Revision ID: 003
Revises: 002
Create Date: 2026-06-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memory_entities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("source_event_id", sa.String(length=36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_entities_tenant_id", "memory_entities", ["tenant_id"])
    op.create_index("ix_memory_entities_user_id", "memory_entities", ["user_id"])
    op.create_index("ix_memory_entities_name", "memory_entities", ["name"])
    op.create_index("ix_memory_entities_entity_type", "memory_entities", ["entity_type"])

    op.create_table(
        "memory_relations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("from_entity_id", sa.String(length=36), nullable=False),
        sa.Column("to_entity_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_event_id", sa.String(length=36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_relations_tenant_id", "memory_relations", ["tenant_id"])
    op.create_index("ix_memory_relations_user_id", "memory_relations", ["user_id"])
    op.create_index("ix_memory_relations_from_entity_id", "memory_relations", ["from_entity_id"])
    op.create_index("ix_memory_relations_to_entity_id", "memory_relations", ["to_entity_id"])
    op.create_index("ix_memory_relations_relation_type", "memory_relations", ["relation_type"])


def downgrade() -> None:
    op.drop_table("memory_relations")
    op.drop_table("memory_entities")