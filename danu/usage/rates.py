"""Approximate list-price rates for cost estimation. Update as providers change."""

from __future__ import annotations

# USD per 1M tokens (OpenAI list prices, approximate)
LLM_RATES_PER_MILLION: dict[str, dict[str, float]] = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "text-embedding-3-small": {"input": 0.02},
}

# USD per unit (Twilio US approximate)
TWILIO_VOICE_MINUTE_USD = 0.0085
TWILIO_SMS_SEGMENT_USD = 0.0079


def estimate_llm_cost_usd(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    rates = LLM_RATES_PER_MILLION.get(model, LLM_RATES_PER_MILLION["gpt-4.1-mini"])
    input_cost = (prompt_tokens / 1_000_000) * rates.get("input", 0.0)
    output_cost = (completion_tokens / 1_000_000) * rates.get("output", 0.0)
    return round(input_cost + output_cost, 6)


def estimate_embedding_cost_usd(*, model: str, total_tokens: int) -> float:
    rates = LLM_RATES_PER_MILLION.get(model, LLM_RATES_PER_MILLION["text-embedding-3-small"])
    return round((total_tokens / 1_000_000) * rates.get("input", 0.02), 6)


def estimate_twilio_voice_cost_usd(*, duration_seconds: int) -> float:
    minutes = max(duration_seconds, 0) / 60.0
    return round(minutes * TWILIO_VOICE_MINUTE_USD, 6)


def estimate_twilio_sms_cost_usd(*, segments: int = 1) -> float:
    return round(max(segments, 1) * TWILIO_SMS_SEGMENT_USD, 6)