from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from danu.agent.llm import LLMClient, get_llm_client
from danu.agent.prompt_builder import build_system_prompt, build_user_prompt
from danu.agent.tools.registry import ToolRegistry, get_default_registry
from danu.channels.base import MessageEnvelope
from danu.config import get_settings
from danu.db.repositories.conversation import ConversationRepository
from danu.db.repositories.task import TaskRepository
from danu.memory.retrieve import MemoryRetriever
from danu.memory.schemas import MemoryOp, MemoryOpType
from danu.memory.store import MemoryStore


@dataclass
class TurnResult:
    response_text: str
    conversation_id: str
    inbound_event_id: str
    outbound_event_id: str


class AgentOrchestrator:
    def __init__(
        self,
        session: Session,
        *,
        llm: LLMClient | None = None,
        tools: ToolRegistry | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.conversations = ConversationRepository(session)
        self.tasks = TaskRepository(session)
        self.store = MemoryStore(session)
        self.retriever = MemoryRetriever(session)
        self.llm = llm or get_llm_client()
        self.tools = tools or get_default_registry()

    def handle_turn(self, envelope: MessageEnvelope) -> TurnResult:
        conversation = self.conversations.get_by_id(envelope.conversation_id)
        if conversation is not None:
            self.conversations.touch(conversation)

        inbound = self.store.append_inbound(
            tenant_id=envelope.tenant_id,
            user_id=envelope.user_id,
            conversation_id=envelope.conversation_id,
            channel=envelope.channel,
            body=envelope.body,
            correlation_id=envelope.correlation_id,
            metadata={"raw_payload": envelope.raw_payload},
        )

        context = self.retriever.retrieve(
            tenant_id=envelope.tenant_id,
            user_id=envelope.user_id,
            conversation_id=envelope.conversation_id,
            query=envelope.body,
        )

        llm_response = self.llm.complete(
            system_prompt=build_system_prompt(channel=envelope.channel),
            user_prompt=build_user_prompt(
                user_message=envelope.body,
                context=context,
                channel=envelope.channel,
            ),
        )

        memory_ops = self._extract_memory_ops(envelope.body, llm_response.memory_ops)
        if memory_ops:
            self.store.stage_memory_ops(
                tenant_id=envelope.tenant_id,
                user_id=envelope.user_id,
                conversation_id=envelope.conversation_id,
                ops=memory_ops,
                channel=envelope.channel,
            )

        outbound = self.store.append_outbound(
            tenant_id=envelope.tenant_id,
            user_id=envelope.user_id,
            conversation_id=envelope.conversation_id,
            channel=envelope.channel,
            body=llm_response.content,
            correlation_id=envelope.correlation_id,
        )

        return TurnResult(
            response_text=llm_response.content,
            conversation_id=envelope.conversation_id,
            inbound_event_id=inbound.id,
            outbound_event_id=outbound.id,
        )

    def resolve_conversation(
        self,
        *,
        tenant_id: str,
        user_id: str,
        channel: str,
        correlation_id: str | None = None,
    ) -> str:
        if correlation_id:
            existing = self.conversations.get_by_correlation_id(correlation_id)
            if existing:
                return existing.id

        if channel == "sms":
            active = self.conversations.get_active_for_user(
                tenant_id=tenant_id,
                user_id=user_id,
                channel=channel,
                idle_minutes=self.settings.sms_conversation_idle_minutes,
            )
            if active:
                return active.id

        conversation = self.conversations.create(
            tenant_id=tenant_id,
            user_id=user_id,
            channel=channel,
            correlation_id=correlation_id,
        )
        return conversation.id

    def close_conversation(self, conversation_id: str) -> None:
        conversation = self.conversations.get_by_id(conversation_id)
        if conversation is None:
            return

        self.conversations.close(conversation)
        self.tasks.enqueue(
            tenant_id=conversation.tenant_id,
            user_id=conversation.user_id,
            task_type="consolidate_memory",
            payload_json={"conversation_id": conversation_id},
        )

    def _extract_memory_ops(self, user_message: str, llm_ops: list[dict]) -> list[MemoryOp]:
        ops: list[MemoryOp] = []
        lowered = user_message.lower()
        if "remember that" in lowered or "remember:" in lowered:
            text = user_message.split("remember that", 1)[-1].split("remember:", 1)[-1].strip()
            if text:
                ops.append(
                    MemoryOp(
                        op_type=MemoryOpType.CREATE,
                        category="instruction",
                        key=f"user_note_{abs(hash(text)) % 10_000}",
                        value={"text": text},
                        confidence=0.95,
                        fast_track=True,
                    )
                )

        for raw in llm_ops:
            ops.append(
                MemoryOp(
                    op_type=MemoryOpType(raw.get("op_type", "create")),
                    category=raw.get("category", "fact"),
                    key=raw.get("key", "unknown"),
                    value=raw.get("value", {}),
                    confidence=float(raw.get("confidence", 0.5)),
                    fast_track=bool(raw.get("fast_track", False)),
                )
            )
        return ops