from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from danu.db.repositories.memory import MemoryRepository
from danu.memory.schemas import MemoryOp, MemoryOpType
from danu.memory.store import MemoryStore

PROFILE_CATEGORY = "profile"

PROFILE_KEYS = (
    "user_name",
    "agent_name",
    "primary_use_case",
    "onboarding_completed",
)


@dataclass
class OnboardingState:
    user_name: str | None = None
    agent_name: str | None = None
    primary_use_case: str | None = None
    completed: bool = False

    @property
    def display_agent_name(self) -> str:
        return self.agent_name or "DANU"

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.user_name:
            missing.append("user_name")
        if not self.agent_name:
            missing.append("agent_name")
        if not self.primary_use_case:
            missing.append("primary_use_case")
        return missing


class OnboardingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.memory = MemoryRepository(session)
        self.store = MemoryStore(session)

    def load_state(self, *, tenant_id: str, user_id: str) -> OnboardingState:
        state = OnboardingState()
        for key in PROFILE_KEYS:
            item = self.memory.get_current_item(tenant_id=tenant_id, user_id=user_id, key=key)
            if item is None:
                continue
            value = item.value_json or {}
            if key == "user_name":
                state.user_name = str(value.get("text", "")).strip() or None
            elif key == "agent_name":
                state.agent_name = str(value.get("text", "")).strip() or None
            elif key == "primary_use_case":
                state.primary_use_case = str(value.get("text", "")).strip() or None
            elif key == "onboarding_completed":
                state.completed = bool(value.get("completed"))
        return state

    def needs_onboarding(self, *, tenant_id: str, user_id: str) -> bool:
        state = self.load_state(tenant_id=tenant_id, user_id=user_id)
        return not state.completed and not self._is_complete(state)

    def mark_completed(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str | None = None,
        channel: str | None = None,
    ) -> None:
        op = MemoryOp(
            op_type=MemoryOpType.CREATE,
            category=PROFILE_CATEGORY,
            key="onboarding_completed",
            value={"completed": True},
            confidence=1.0,
            fast_track=True,
        )
        self.store.stage_memory_ops(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id or "onboarding",
            ops=[op],
            channel=channel,
        )

    def save_profile_field(
        self,
        *,
        tenant_id: str,
        user_id: str,
        field: str,
        value: str,
        conversation_id: str,
        channel: str | None = None,
    ) -> None:
        if field not in {"user_name", "agent_name", "primary_use_case"}:
            raise ValueError(f"Unsupported profile field: {field}")

        op = MemoryOp(
            op_type=MemoryOpType.CREATE,
            category=PROFILE_CATEGORY,
            key=field,
            value={"text": value.strip()},
            confidence=0.95,
            fast_track=True,
        )
        self.store.stage_memory_ops(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            ops=[op],
            channel=channel,
        )

    def voice_greeting(self, *, tenant_id: str, user_id: str) -> str:
        state = self.load_state(tenant_id=tenant_id, user_id=user_id)
        if self.needs_onboarding(tenant_id=tenant_id, user_id=user_id):
            return (
                "Hey! I'm your new assistant. "
                "Looks like this is our first time talking. "
                "What should I call you?"
            )
        return f"Hey, it's {state.display_agent_name}. What's up?"

    def _is_complete(self, state: OnboardingState) -> bool:
        return bool(state.user_name and state.agent_name)