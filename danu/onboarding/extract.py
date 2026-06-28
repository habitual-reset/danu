from __future__ import annotations

import re

from danu.memory.schemas import MemoryOp, MemoryOpType
from danu.onboarding.service import PROFILE_CATEGORY, OnboardingState

_NAME_PREFIXES = (
    r"my name is",
    r"i'm",
    r"i am",
    r"call me",
    r"it's",
    r"this is",
    r"name's",
    r"name is",
)

_AGENT_PREFIXES = (
    r"call you",
    r"name you",
    r"your name is",
    r"you're",
    r"you are",
    r"i'll call you",
    r"ill call you",
)


def extract_onboarding_ops(state: OnboardingState, user_message: str) -> list[MemoryOp]:
    text = user_message.strip()
    if not text:
        return []

    ops: list[MemoryOp] = []
    lowered = text.lower()

    if not state.user_name:
        name = _extract_user_name(text, lowered)
        if name:
            ops.append(_profile_op("user_name", name))
            return ops

    if not state.agent_name:
        agent = _extract_agent_name(text, lowered)
        if agent:
            ops.append(_profile_op("agent_name", agent))
            return ops

    if not state.primary_use_case and state.user_name and state.agent_name:
        use_case = _extract_use_case(text, lowered)
        if use_case:
            ops.append(_profile_op("primary_use_case", use_case))

    return ops


def _profile_op(key: str, value: str) -> MemoryOp:
    return MemoryOp(
        op_type=MemoryOpType.CREATE,
        category=PROFILE_CATEGORY,
        key=key,
        value={"text": value},
        confidence=0.95,
        fast_track=True,
    )


def _extract_user_name(text: str, lowered: str) -> str | None:
    for prefix in _NAME_PREFIXES:
        match = re.search(rf"{prefix}\s+(.+)", lowered)
        if match:
            return _clean_name(text[match.start(1) : match.end(1)])

    if len(text.split()) <= 3 and not _looks_like_question(lowered):
        cleaned = _clean_name(text)
        if cleaned and len(cleaned) >= 2:
            return cleaned
    return None


def _extract_agent_name(text: str, lowered: str) -> str | None:
    for prefix in _AGENT_PREFIXES:
        match = re.search(rf"{prefix}\s+(.+)", lowered)
        if match:
            return _clean_name(text[match.start(1) : match.end(1)])
    return None


def _extract_use_case(text: str, lowered: str) -> str | None:
    if _looks_like_question(lowered):
        return None
    if len(text) < 8:
        return None
    skip_phrases = ("that's it", "that's all", "nothing else", "no thanks", "goodbye", "bye")
    if any(phrase in lowered for phrase in skip_phrases):
        return None
    return text.strip().rstrip(".")


def _clean_name(value: str) -> str | None:
    cleaned = value.strip().strip(".,!?")
    if not cleaned:
        return None
    words = cleaned.split()
    if len(words) > 4:
        return None
    if len(words) >= 2 and len({word.lower() for word in words}) == 1:
        words = [words[0]]
    return " ".join(word.capitalize() for word in words)


def _looks_like_question(lowered: str) -> bool:
    return "?" in lowered or lowered.startswith(
        ("what", "how", "can you", "do you", "are you", "who", "why", "when", "where")
    )