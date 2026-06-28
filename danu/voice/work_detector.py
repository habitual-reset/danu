from __future__ import annotations

import re

_TASK_KEYWORDS = (
    "task",
    "remind me",
    "remember to",
    "need to",
    "have to",
    "todo",
    "to do",
    "add ",
    "track",
    "deadline",
    "priority",
    "schedule",
)

_SHORT_ACKS = {
    "yes",
    "yeah",
    "yep",
    "okay",
    "ok",
    "sure",
    "sounds good",
    "sounds okay",
    "sounds reasonable",
    "got it",
    "thanks",
    "thank you",
    "no",
    "nope",
}


def needs_hold(
    speech: str,
    *,
    onboarding_complete: bool,
    min_words_for_hold: int = 12,
) -> bool:
    text = speech.strip()
    if not text:
        return False

    lowered = text.lower().rstrip(".!?")

    if lowered in _SHORT_ACKS or len(lowered.split()) <= 4:
        return False

    if _is_retrieval_question(lowered):
        return False

    if not onboarding_complete:
        return len(text.split()) >= 8

    if any(keyword in lowered for keyword in _TASK_KEYWORDS):
        return True

    return len(text.split()) >= min_words_for_hold


def _is_retrieval_question(lowered: str) -> bool:
    prefixes = (
        "what tasks",
        "what do i have",
        "can you tell me",
        "do you know",
        "what did i",
        "remind me what",
        "list my",
    )
    return lowered.startswith(prefixes) or lowered.endswith("?") and any(
        p in lowered for p in ("what ", "tell me", "do you know", "can you")
    )


def classify_work_type(speech: str) -> str:
    lowered = speech.lower()
    if any(keyword in lowered for keyword in _TASK_KEYWORDS):
        return "task_memory"
    return "think"


def estimate_seconds(speech: str, *, work_type: str) -> int:
    words = len(speech.split())
    base = 5
    if work_type == "task_memory":
        base = 7
    if words > 25:
        base += 3
    if words > 50:
        base += 3
    return min(base, 15)


def hold_message(
    *,
    work_type: str,
    estimated_seconds: int,
    agent_name: str = "DANU",
    onboarding: bool = False,
) -> str:
    seconds = max(estimated_seconds, 3)
    if onboarding:
        return (
            f"Thanks. Give me about {seconds} seconds — "
            f"I want to make sure I get this right."
        )
    if work_type == "task_memory":
        return (
            f"Got it. Give me about {seconds} seconds — "
            f"I'm going to jot that down and think it through."
        )
    return (
        f"Okay. Give me about {seconds} seconds to work on that. "
        f"I'll be right back."
    )


def still_working_message(*, agent_name: str = "DANU") -> str:
    return f"Still working on that. Hang tight."