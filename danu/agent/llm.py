from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from danu.config import get_settings


@dataclass
class LLMResponse:
    content: str
    memory_ops: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMClient(ABC):
    @abstractmethod
    def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        return LLMResponse(content=f"You said: {user_prompt}")


class OpenAILLMClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        return LLMResponse(
            content=content,
            model=self.model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )


def get_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAILLMClient(settings.openai_api_key, settings.llm_model)
    return MockLLMClient()


def get_consolidation_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAILLMClient(settings.openai_api_key, settings.llm_consolidation_model)
    return MockLLMClient()