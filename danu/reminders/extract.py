from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass
class ReminderRequest:
    message: str
    fire_at: datetime


_TIME_PATTERNS = (
    re.compile(
        r"remind(?:er)?(?:\s+me)?\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)",
        re.I,
    ),
    re.compile(
        r"remind(?:er)?(?:\s+me)?\s+at\s+(\d{1,2}):(\d{2})",
        re.I,
    ),
)


def extract_reminder_requests(
    user_message: str,
    *,
    timezone: str = "America/New_York",
    now: datetime | None = None,
) -> list[ReminderRequest]:
    text = user_message.strip()
    if not text or "remind" not in text.lower():
        return []

    tz = ZoneInfo(timezone)
    current = now or datetime.now(tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)

    for pattern in _TIME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = (match.group(3) or "").lower()
        if meridiem:
            mer = meridiem.replace(".", "")
            if mer == "pm" and hour != 12:
                hour += 12
            if mer == "am" and hour == 12:
                hour = 0

        fire_at = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if fire_at <= current:
            fire_at += timedelta(days=1)

        message = _default_reminder_message(text)
        return [ReminderRequest(message=message, fire_at=fire_at)]

    return []


def _default_reminder_message(text: str) -> str:
    lowered = text.lower()
    if "check in" in lowered or "progress" in lowered:
        return "Time to check in on your tasks — how much did you get done?"
    if "task" in lowered:
        return "Reminder from Sid: time for your scheduled task check-in."
    return "Reminder from your assistant."