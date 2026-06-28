"""Background memory consolidation with LLM summarization and fact extraction."""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from danu.agent.llm import LLMClient, get_consolidation_llm_client
from danu.db.repositories.event import EventRepository
from danu.db.repositories.memory import MemoryRepository
from danu.db.repositories.memory_graph import MemoryGraphRepository
from danu.db.repositories.message import MessageRepository
from danu.memory.schemas import MemoryOp, MemoryOpType
from danu.memory.store import MemoryStore
from danu.usage.tracker import UsageTracker


class MemoryConsolidator:
    def __init__(self, session: Session, *, llm: LLMClient | None = None) -> None:
        self.session = session
        self.events = EventRepository(session)
        self.messages = MessageRepository(session)
        self.memory = MemoryRepository(session)
        self.graph = MemoryGraphRepository(session)
        self.store = MemoryStore(session)
        self.llm = llm or get_consolidation_llm_client()

    def consolidate_conversation(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        min_messages: int = 2,
    ) -> str | None:
        messages = self.messages.list_recent(conversation_id, limit=200)
        if len(messages) < min_messages:
            return None

        transcript = "\n".join(f"{msg.role}: {msg.content}" for msg in messages)
        summary, facts, entities, relations = self._llm_extract(
            transcript,
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if not summary:
            summary = "Conversation summary:\n" + "\n".join(
                f"{msg.role}: {msg.content}" for msg in messages[-6:]
            )

        self.memory.add_summary(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            summary=summary,
            period_start=messages[0].created_at,
            period_end=messages[-1].created_at,
        )

        for fact in facts:
            self.store.commit_memory_op(
                tenant_id=tenant_id,
                user_id=user_id,
                op=MemoryOp(
                    op_type=MemoryOpType.CREATE,
                    category=fact.get("category", "fact"),
                    key=fact.get("key", "extracted_fact"),
                    value=fact.get("value", {}),
                    confidence=float(fact.get("confidence", 0.75)),
                ),
                source_event_id="consolidation",
            )

        self._persist_graph(
            tenant_id=tenant_id,
            user_id=user_id,
            entities=entities,
            relations=relations,
        )

        return summary

    def _persist_graph(
        self,
        *,
        tenant_id: str,
        user_id: str,
        entities: list[dict],
        relations: list[dict],
    ) -> None:
        entity_ids: dict[tuple[str, str], str] = {}

        for raw in entities:
            name = str(raw.get("name", "")).strip()
            entity_type = str(raw.get("entity_type", "thing")).strip().lower()
            if not name:
                continue
            row = self.graph.upsert_entity(
                tenant_id=tenant_id,
                user_id=user_id,
                name=name,
                entity_type=entity_type,
                source_event_id="consolidation",
            )
            entity_ids[(name.lower(), entity_type)] = row.id

        for raw in relations:
            from_name = str(raw.get("from_name", "")).strip()
            to_name = str(raw.get("to_name", "")).strip()
            from_type = str(raw.get("from_type", "thing")).strip().lower()
            to_type = str(raw.get("to_type", "thing")).strip().lower()
            relation_type = str(raw.get("relation_type", "related_to")).strip().lower()
            if not from_name or not to_name:
                continue

            from_id = entity_ids.get((from_name.lower(), from_type))
            to_id = entity_ids.get((to_name.lower(), to_type))
            if not from_id:
                from_id = self.graph.upsert_entity(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    name=from_name,
                    entity_type=from_type,
                    source_event_id="consolidation",
                ).id
            if not to_id:
                to_id = self.graph.upsert_entity(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    name=to_name,
                    entity_type=to_type,
                    source_event_id="consolidation",
                ).id

            self.graph.add_relation(
                tenant_id=tenant_id,
                user_id=user_id,
                from_entity_id=from_id,
                to_entity_id=to_id,
                relation_type=relation_type,
                confidence=float(raw.get("confidence", 0.7)),
                source_event_id="consolidation",
            )

    def _llm_extract(
        self,
        transcript: str,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
    ) -> tuple[str, list[dict], list[dict], list[dict]]:
        system = (
            "You extract durable memory from conversations. "
            "Return ONLY valid JSON with keys: summary (string), facts (array), "
            "entities (array), relations (array). "
            "Each fact: category (preference|person|project|instruction|fact), "
            "key (snake_case), value (object with text field), confidence (0-1). "
            "Each entity: name (string), entity_type (person|place|project|thing). "
            "Each relation: from_name, to_name, from_type, to_type, "
            "relation_type (knows|works_on|prefers|located_in|related_to), confidence (0-1). "
            "Only include durable facts and entities likely to matter later. Max 5 facts, 5 entities, 5 relations."
        )
        user = f"Transcript:\n{transcript}\n\nReturn JSON."

        try:
            response = self.llm.complete(system_prompt=system, user_prompt=user)
            UsageTracker(self.session).record_llm_completion(
                tenant_id=tenant_id,
                user_id=user_id,
                model=response.model,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                conversation_id=conversation_id,
                purpose="consolidation",
            )
            return self._parse_extraction(response.content)
        except Exception:
            return "", [], [], []

    def _parse_extraction(
        self, content: str
    ) -> tuple[str, list[dict], list[dict], list[dict]]:
        text = content.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return "", [], [], []
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return "", [], [], []

        summary = str(data.get("summary", "")).strip()
        facts = data.get("facts", [])
        entities = data.get("entities", [])
        relations = data.get("relations", [])
        if not isinstance(facts, list):
            facts = []
        if not isinstance(entities, list):
            entities = []
        if not isinstance(relations, list):
            relations = []
        return summary, facts[:5], entities[:5], relations[:5]

    def process_proposed_events(
        self,
        *,
        tenant_id: str,
        user_id: str,
        confidence_threshold: float = 0.8,
    ) -> int:
        from danu.db.models.event import Event
        from sqlalchemy import select

        stmt = (
            select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.user_id == user_id,
                Event.event_type == "memory.proposed",
            )
            .order_by(Event.created_at.asc())
        )
        events = list(self.session.scalars(stmt).all())
        committed = 0

        committed_event_ids = {
            e.payload_json.get("source_event_id")
            for e in self.session.scalars(
                select(Event).where(
                    Event.tenant_id == tenant_id,
                    Event.event_type == "memory.committed",
                )
            ).all()
        }

        for event in events:
            if event.id in committed_event_ids:
                continue

            for raw_op in event.payload_json.get("ops", []):
                confidence = float(raw_op.get("confidence", 0.5))
                if confidence < confidence_threshold and not raw_op.get("fast_track"):
                    continue

                op = MemoryOp(
                    op_type=MemoryOpType(raw_op["op_type"]),
                    category=raw_op["category"],
                    key=raw_op["key"],
                    value=raw_op["value"],
                    confidence=confidence,
                    fast_track=bool(raw_op.get("fast_track")),
                )
                self.store.commit_memory_op(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    op=op,
                    source_event_id=event.id,
                )
                committed += 1

        return committed