"""Reset per-user runtime data while keeping schema and code intact."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from danu.db.models.conversation import Conversation
from danu.db.models.event import Event
from danu.db.models.memory import ConversationSummary, MemoryEmbedding, MemoryItem
from danu.db.models.memory_graph import MemoryEntity, MemoryRelation
from danu.db.models.message import Message
from danu.db.models.task import Task
from danu.db.models.usage_event import UsageEvent
from danu.db.models.voice_hold_job import VoiceHoldJob


def reset_onboarding_experience(
    session: Session,
    *,
    tenant_id: str,
    user_id: str,
    keep_usage: bool = False,
) -> dict[str, int]:
    """Wipe user runtime data so the next call is a fresh onboarding experience.

    Clears profile (name, agent name, onboarding_completed), memory, conversations,
    and hold jobs. Schema, code, and allowlist are untouched.
    """
    return reset_user_data(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        keep_usage=keep_usage,
    )


def reset_user_data(
    session: Session,
    *,
    tenant_id: str,
    user_id: str,
    keep_usage: bool = False,
) -> dict[str, int]:
    """Delete conversations, memory, and messages for a user. Returns row counts."""
    counts: dict[str, int] = {}

    tables = [
        (MemoryEmbedding, "memory_embeddings"),
        (MemoryRelation, "memory_relations"),
        (MemoryEntity, "memory_entities"),
        (ConversationSummary, "conversation_summaries"),
        (MemoryItem, "memory_items"),
        (Message, "messages"),
        (Event, "events"),
        (Task, "tasks"),
        (Conversation, "conversations"),
        (VoiceHoldJob, "voice_hold_jobs"),
    ]
    if not keep_usage:
        tables.append((UsageEvent, "usage_events"))

    for model, label in tables:
        stmt = delete(model).where(
            model.tenant_id == tenant_id,
            model.user_id == user_id,
        )
        result = session.execute(stmt)
        counts[label] = result.rowcount or 0

    session.flush()
    return counts