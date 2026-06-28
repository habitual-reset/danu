from __future__ import annotations

from sqlalchemy.orm import Session

from danu.db.repositories.event import EventRepository
from danu.db.repositories.memory import MemoryRepository
from danu.db.repositories.message import MessageRepository
from danu.memory.embeddings import get_embedding_backend
from danu.usage.tracker import UsageTracker
from danu.memory.schemas import MemoryOp, MemoryOpType, ProposedMemory


class MemoryStore:
    """Write path: persist events before any downstream thinking."""

    FAST_TRACK_CONFIDENCE = 0.95
    COMMIT_THRESHOLD = 0.8

    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = EventRepository(session)
        self.messages = MessageRepository(session)
        self.memory = MemoryRepository(session)
        self.embeddings = get_embedding_backend()

    def append_inbound(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        channel: str,
        body: str,
        correlation_id: str | None = None,
        metadata: dict | None = None,
    ):
        payload = {"content": body, **(metadata or {})}
        event = self.events.append(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            event_type="message.inbound",
            payload_json=payload,
            channel=channel,
            correlation_id=correlation_id,
        )
        self.messages.add(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            role="user",
            content=body,
            source_event_id=event.id,
        )
        return event

    def append_outbound(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        channel: str,
        body: str,
        correlation_id: str | None = None,
        metadata: dict | None = None,
    ):
        payload = {"content": body, **(metadata or {})}
        event = self.events.append(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            event_type="message.outbound",
            payload_json=payload,
            channel=channel,
            correlation_id=correlation_id,
        )
        self.messages.add(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            role="assistant",
            content=body,
            source_event_id=event.id,
        )
        return event

    def stage_memory_ops(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        ops: list[MemoryOp],
        channel: str | None = None,
    ) -> ProposedMemory:
        serialized_ops = [
            {
                "op_type": op.op_type.value,
                "category": op.category,
                "key": op.key,
                "value": op.value,
                "confidence": op.confidence,
                "fast_track": op.fast_track,
            }
            for op in ops
        ]
        event = self.events.append(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            event_type="memory.proposed",
            payload_json={"ops": serialized_ops},
            channel=channel,
        )
        proposed = ProposedMemory(event_id=event.id, ops=ops)
        self._commit_fast_track(tenant_id=tenant_id, user_id=user_id, proposed=proposed)
        return proposed

    def commit_memory_op(
        self,
        *,
        tenant_id: str,
        user_id: str,
        op: MemoryOp,
        source_event_id: str,
    ):
        confidence = op.confidence
        if op.fast_track:
            confidence = max(confidence, self.FAST_TRACK_CONFIDENCE)

        item = self.memory.add_item(
            tenant_id=tenant_id,
            user_id=user_id,
            category=op.category,
            key=op.key,
            value_json=op.value,
            confidence=confidence,
            source_event_id=source_event_id,
        )

        chunk_text = f"{op.category}:{op.key} {op.value}"
        embedding_result = self.embeddings.embed(chunk_text)
        self.memory.upsert_embedding(
            tenant_id=tenant_id,
            user_id=user_id,
            source_type="memory_item",
            source_id=item.id,
            chunk_text=chunk_text,
            embedding=embedding_result.vector,
        )
        UsageTracker(self.session).record_embedding(
            tenant_id=tenant_id,
            user_id=user_id,
            model=embedding_result.model or "text-embedding-3-small",
            total_tokens=embedding_result.total_tokens,
            purpose="memory_commit",
        )

        commit_event = self.events.append(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=None,
            event_type="memory.committed",
            payload_json={
                "memory_item_id": item.id,
                "source_event_id": source_event_id,
                "key": op.key,
            },
        )
        return item, commit_event

    def _commit_fast_track(
        self,
        *,
        tenant_id: str,
        user_id: str,
        proposed: ProposedMemory,
    ) -> None:
        for op in proposed.ops:
            confidence = op.confidence
            if op.fast_track:
                confidence = max(confidence, self.FAST_TRACK_CONFIDENCE)
            if confidence >= self.COMMIT_THRESHOLD or op.fast_track:
                self.commit_memory_op(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    op=op,
                    source_event_id=proposed.event_id,
                )

    def log_tool_invocation(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        tool_name: str,
        arguments: dict,
        result: dict,
        channel: str | None = None,
    ):
        return self.events.append(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            event_type="tool.invoked",
            payload_json={
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result,
            },
            channel=channel,
        )