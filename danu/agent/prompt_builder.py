from danu.memory.schemas import ContextPack


def build_system_prompt() -> str:
    return (
        "You are a reliable personal assistant. "
        "Use provided memory facts when relevant. "
        "Be concise and accurate. "
        "If the user asks you to remember something, acknowledge it clearly."
    )


def build_user_prompt(*, user_message: str, context: ContextPack) -> str:
    sections: list[str] = []

    if context.system_facts:
        facts = "\n".join(
            f"- {fact.key}: {fact.value} {fact.provenance}"
            for fact in context.system_facts
        )
        sections.append(f"Standing instructions:\n{facts}")

    if context.relevant_facts:
        facts = "\n".join(
            f"- {fact.key}: {fact.value} {fact.provenance}"
            for fact in context.relevant_facts
        )
        sections.append(f"Relevant memory:\n{facts}")

    if context.session_summary:
        sections.append(f"Session summary:\n{context.session_summary}")

    if context.recent_messages:
        history = "\n".join(
            f"{msg.role}: {msg.content}" for msg in context.recent_messages[-6:]
        )
        sections.append(f"Recent conversation:\n{history}")

    sections.append(f"User message:\n{user_message}")
    return "\n\n".join(sections)