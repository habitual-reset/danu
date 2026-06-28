from __future__ import annotations

from danu.config import get_settings


def phone_for_user(user_id: str) -> str | None:
    settings = get_settings()
    for phone, mapped_user in settings.allowlist.items():
        if mapped_user == user_id:
            return phone
    return None