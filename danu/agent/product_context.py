"""Standing product context — keeps the agent aligned with what DANU is becoming."""

PRODUCT_VISION = (
    "DANU is a phone-first personal agent: call or text your number, get a persistent "
    "assistant that remembers you. Architecture: voice/SMS channels → orchestrator → "
    "memory (event-sourced) → background worker (reminders, consolidation). "
    "Future: web portal to connect tools; each user gets isolated memory + job queue "
    "(their 'virtual computer'). MVP loops: onboarding by phone, task memory, "
    "voice turn → scheduled SMS reminder → outbound text when due."
)


def build_product_context_section() -> str:
    return f"Product context (what we are building):\n{PRODUCT_VISION}"