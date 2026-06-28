from danu.agent.product_context import build_product_context_section
from danu.channels.base import ChannelType
from danu.memory.schemas import ContextPack
from danu.onboarding.service import OnboardingState


def build_system_prompt(
    channel: ChannelType = "sms",
    *,
    onboarding: OnboardingState | None = None,
    in_onboarding: bool = False,
) -> str:
    if in_onboarding and onboarding is not None:
        return _build_onboarding_system_prompt(channel=channel, state=onboarding)

    agent_name = onboarding.display_agent_name if onboarding else "DANU"
    base = (
        f"You are a reliable personal assistant named {agent_name}. "
        "Use provided memory facts when relevant. "
        "Be accurate. If the user asks you to remember something, acknowledge it clearly. "
        "When the user requests a reminder, confirm you scheduled an SMS text for that time. "
        "SMS reminders are queued by the system; outbound delivery may wait on carrier approval. "
        "Never claim push notifications or app alerts — only SMS from this assistant's number."
    )
    product = build_product_context_section()
    if channel == "voice":
        return (
            base
            + " You are on a live phone call. "
            "Reply in 1-3 short spoken sentences only. "
            "No bullet points, lists, markdown, or URLs. "
            "Sound natural, warm, and direct — like a helpful human on the phone.\n\n"
            + product
        )
    return base + " Be concise.\n\n" + product


def _build_onboarding_system_prompt(*, channel: ChannelType, state: OnboardingState) -> str:
    progress_lines = [
        f"- User's name: {state.user_name or 'not set yet'}",
        f"- Your name: {state.agent_name or 'not set yet (default DANU)'}",
        f"- Main help needed: {state.primary_use_case or 'not set yet'}",
    ]
    progress = "\n".join(progress_lines)

    base = (
        "You are a new personal assistant meeting your user for the first time. "
        "This is onboarding — learn who they are and what they need.\n\n"
        f"Progress:\n{progress}\n\n"
        "Rules:\n"
        "- Ask exactly ONE question at a time for the next missing item.\n"
        "- Order: user's name first, then what they want to call you, then what they mainly need help with.\n"
        "- When all three are set, welcome them warmly and confirm you're ready.\n"
        "- Be warm and human, not robotic or salesy."
    )
    if channel == "voice":
        return (
            base
            + " You are on a live phone call. "
            "Reply in 1-3 short spoken sentences only. "
            "No bullet points, lists, markdown, or URLs."
        )
    return base + " Be concise."


def build_user_prompt(
    *,
    user_message: str,
    context: ContextPack,
    channel: ChannelType = "sms",
    onboarding: OnboardingState | None = None,
) -> str:
    sections: list[str] = []

    if onboarding is not None and not onboarding.completed:
        missing = onboarding.missing_fields()
        if missing:
            sections.append(f"Onboarding: still need {', '.join(missing)}.")

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