"""Embedding backend abstraction. MVP uses a simple hash-based stub when no API key is set."""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from danu.config import get_settings


@dataclass
class EmbeddingResult:
    vector: list[float]
    model: str = ""
    total_tokens: int = 0


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingBackend(ABC):
    @abstractmethod
    def embed(self, text: str) -> EmbeddingResult:
        raise NotImplementedError


class StubEmbeddingBackend(EmbeddingBackend):
    """Deterministic local embeddings for development and tests."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> EmbeddingResult:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [digest[i % len(digest)] / 255.0 for i in range(self.dimensions)]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return EmbeddingResult(vector=[v / norm for v in values])


class OpenAIEmbeddingBackend(EmbeddingBackend):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed(self, text: str) -> EmbeddingResult:
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        usage = response.usage
        return EmbeddingResult(
            vector=list(response.data[0].embedding),
            model=self.model,
            total_tokens=usage.total_tokens if usage else 0,
        )


def get_embedding_backend() -> EmbeddingBackend:
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAIEmbeddingBackend(settings.openai_api_key)
    return StubEmbeddingBackend()


def rank_by_similarity(
    query_embedding: list[float],
    candidates: list[tuple[str, list[float], str]],
    top_k: int,
) -> list[tuple[str, float, str]]:
    scored = [
        (source_id, _cosine_similarity(query_embedding, embedding), chunk_text)
        for source_id, embedding, chunk_text in candidates
        if embedding
    ]
    scored.sort(key=lambda row: row[1], reverse=True)
    return scored[:top_k]