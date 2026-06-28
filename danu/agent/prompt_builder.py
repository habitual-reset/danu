from danu.channels.base import ChannelType
from danu.memory.schemas import ContextPack


def build_system_prompt(channel: ChannelType = "sms") -> str:
    base = (
        "You are a reliable personal assistant named DANU. "
        "Use provided memory facts when relevant. "
        "Be accurate. If the user asks you to remember something, acknowledge it clearly."
    )
    if channel == "voice":
        return (
            base
            + " You are on a live phone call. "
            "Reply in 1-3 short spoken sentences only. "
            "No bullet points, lists, markdown, or URLs. "
            "Sound natural, warm, and direct — like a helpful human on the phone."
        )
    return base + " Be concise."


def build_user_prompt(*, user_message: str, context: ContextPack, channel: ChannelType = "sms") -> str:
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
        limit = 4 if channel == "voice" else 6
        history = "\n".join(
            f"{msg.role}: {msg.content}" for msg in context.recent_messages[-limit:]
        )
        sections.append(f"Recent conversation:\n{history}")

    sections.append(f"User message:\n{user_message}")
    return "\n\n".join(sections)