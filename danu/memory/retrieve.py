from __future__ import annotations

from sqlalchemy.orm import Session

from danu.config import get_settings
from danu.db.models.memory import MemoryItem
from danu.db.repositories.memory import MemoryRepository
from danu.db.repositories.message import MessageRepository
from danu.memory.embeddings import get_embedding_backend, rank_by_similarity
from danu.usage.tracker import UsageTracker
from danu.memory.schemas import ContextPack, ConversationMessage, MemoryFact


class MemoryRetriever:
    """Read path: assemble a token-budgeted context pack with provenance."""

    INSTRUCTION_CATEGORY = "instruction"

    def __init__(self, session: Session) -> None:
        self.session = session
        self.memory = MemoryRepository(session)
        self.messages = MessageRepository(session)
        self.embeddings = get_embedding_backend()
        self.settings = get_settings()

    def retrieve(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        query: str,
        token_budget: int | None = None,
    ) -> ContextPack:
        budget = token_budget or self.settings.memory_context_token_budget

        system_items = self.memory.list_current_items(
            tenant_id=tenant_id,
            user_id=user_id,
            category=self.INSTRUCTION_CATEGORY,
            limit=5,
        )
        system_facts = [self._to_fact(item) for item in system_items]

        keyword_hits = self.memory.search_items_by_keyword(
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
            limit=self.settings.memory_semantic_top_k,
        )
        semantic_hits = self._semantic_search(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            query=query,
        )

        relevant_facts = self._merge_facts(keyword_hits, semantic_hits)

        recent = self.messages.list_recent(
            conversation_id,
            limit=self.settings.memory_recent_message_limit,
        )
        recent_messages = [
            ConversationMessage(role=msg.role, content=msg.content, created_at=msg.created_at.isoformat())
            for msg in recent
        ]

        summaries = self.memory.list_summaries(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            limit=1,
        )
        session_summary = summaries[0].summary if summaries else None

        pack = ContextPack(
            system_facts=system_facts,
            relevant_facts=relevant_facts,
            recent_messages=recent_messages,
            session_summary=session_summary,
        )
        pack.token_estimate = self._estimate_tokens(pack)
        return self._trim_to_budget(pack, budget)

    def _semantic_search(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        query: str,
    ) -> list[MemoryFact]:
        rows = self.memory.list_embeddings(tenant_id=tenant_id, user_id=user_id)
        if not rows:
            return []

        embedding_result = self.embeddings.embed(query)
        if embedding_result.total_tokens > 0:
            UsageTracker(self.session).record_embedding(
                tenant_id=tenant_id,
                user_id=user_id,
                model=embedding_result.model or "text-embedding-3-small",
                total_tokens=embedding_result.total_tokens,
                conversation_id=conversation_id,
                purpose="memory_retrieve",
            )
        candidates = [(row.source_id, row.embedding_json, row.chunk_text) for row in rows]
        ranked = rank_by_similarity(
            embedding_result.vector,
            candidates,
            top_k=self.settings.memory_semantic_top_k,
        )

        facts: list[MemoryFact] = []
        for source_id, _score, _chunk in ranked:
            item = self.session.get(MemoryItem, source_id)
            if item and item.superseded_by_id is None and item.valid_to is None:
                facts.append(self._to_fact(item))
        return facts

    def _merge_facts(self, keyword_hits, semantic_hits) -> list[MemoryFact]:
        seen: set[str] = set()
        merged: list[MemoryFact] = []
        for item in keyword_hits:
            fact = self._to_fact(item)
            if fact.id not in seen:
                seen.add(fact.id)
                merged.append(fact)
        for fact in semantic_hits:
            if fact.id not in seen:
                seen.add(fact.id)
                merged.append(fact)
        return merged

    def _to_fact(self, item) -> MemoryFact:
        return MemoryFact(
            id=item.id,
            category=item.category,
            key=item.key,
            value=item.value_json,
            confidence=item.confidence,
            provenance=f"[memory:{item.id}]",
        )

    def _estimate_tokens(self, pack: ContextPack) -> int:
        parts = [pack.session_summary or ""]
        for fact in pack.system_facts + pack.relevant_facts:
            parts.append(f"{fact.key} {fact.value}")
        for msg in pack.recent_messages:
            parts.append(msg.content)
        text = " ".join(parts)
        return max(1, len(text) // 4)

    def _trim_to_budget(self, pack: ContextPack, budget: int) -> ContextPack:
        if pack.token_estimate <= budget:
            return pack

        trimmed_messages = list(pack.recent_messages)
        while trimmed_messages and self._estimate_tokens(
            ContextPack(
                system_facts=pack.system_facts,
                relevant_facts=pack.relevant_facts,
                recent_messages=trimmed_messages,
                session_summary=pack.session_summary,
            )
        ) > budget:
            trimmed_messages.pop(0)

        pack.recent_messages = trimmed_messages
        pack.token_estimate = self._estimate_tokens(pack)
        return pack