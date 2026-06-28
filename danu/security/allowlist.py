from __future__ import annotations

from danu.config import get_settings


def resolve_user_from_phone(phone_number: str) -> str | None:
    settings = get_settings()
    return settings.allowlist.get(phone_number)