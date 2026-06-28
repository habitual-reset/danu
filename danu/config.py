from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/danu.db"

    default_tenant_id: str = "default"
    default_user_id: str = "matt"

    allowlist_phones: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    public_webhook_base_url: str = ""

    openai_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    llm_consolidation_model: str = "gpt-4.1-mini"

    iphone_bridge_api_key: str = ""

    memory_context_token_budget: int = 4000
    memory_recent_message_limit: int = 20
    memory_semantic_top_k: int = 10
    sms_conversation_idle_minutes: int = 30

    def twilio_webhook_url_for(self, path: str) -> str:
        base = self.public_webhook_base_url.rstrip("/")
        if base:
            return f"{base}{path}"
        return path

    @property
    def allowlist(self) -> dict[str, str]:
        """Map E.164 phone numbers to user IDs."""
        mapping: dict[str, str] = {}
        for entry in self.allowlist_phones.split(","):
            phone = entry.strip()
            if phone:
                mapping[phone] = self.default_user_id
        return mapping


@lru_cache
def get_settings() -> Settings:
    return Settings()