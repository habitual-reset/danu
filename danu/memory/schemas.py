from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MemoryOpType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    SUPERSEDE = "supersede"


@dataclass
class MemoryOp:
    op_type: MemoryOpType
    category: str
    key: str
    value: dict
    confidence: float = 0.5
    fast_track: bool = False


@dataclass
class ProposedMemory:
    event_id: str
    ops: list[MemoryOp]


@dataclass
class MemoryFact:
    id: str
    category: str
    key: str
    value: dict
    confidence: float
    provenance: str


@dataclass
class ConversationMessage:
    role: str
    content: str
    created_at: str | None = None


@dataclass
class ContextPack:
    system_facts: list[MemoryFact] = field(default_factory=list)
    relevant_facts: list[MemoryFact] = field(default_factory=list)
    recent_messages: list[ConversationMessage] = field(default_factory=list)
    session_summary: str | None = None
    token_estimate: int = 0