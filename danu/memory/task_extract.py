from __future__ import annotations

import re

from danu.memory.schemas import MemoryOp, MemoryOpType

_TASK_PATTERNS = (
    r"my (?:first )?task is (.+)",
    r"(?:add|create) (?:a )?task(?: to| for)? (.+)",
    r"i need to (.+)",
    r"remind me to (.+)",
    r"remember to (.+)",
    r"i have to (.+)",
)


def extract_task_ops(user_message: str) -> list[MemoryOp]:
    text = user_message.strip()
    if not text:
        return []

    lowered = text.lower()
    for pattern in _TASK_PATTERNS:
        match = re.search(pattern, lowered)
        if not match:
            continue
        task_text = text[match.start(1) : match.end(1)].strip().rstrip(".!?")
        if len(task_text) < 4:
            continue
        return [
            MemoryOp(
                op_type=MemoryOpType.CREATE,
                category="task",
                key=f"task_{abs(hash(task_text)) % 10_000}",
                value={"text": task_text, "status": "open"},
                confidence=0.95,
                fast_track=True,
            )
        ]
    return []