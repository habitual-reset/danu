from __future__ import annotations

from typing import Any

from twilio.twiml.messaging_response import MessagingResponse

from danu.channels.base import MessageEnvelope

SMS_MAX_LENGTH = 1600


def parse_twilio_sms(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "from_number": payload.get("From", "").strip(),
        "to_number": payload.get("To", "").strip(),
        "body": payload.get("Body", "").strip(),
        "message_sid": payload.get("MessageSid", "").strip(),
        "account_sid": payload.get("AccountSid", "").strip(),
        "num_media": payload.get("NumMedia", "0").strip(),
    }


def build_sms_envelope(
    *,
    tenant_id: str,
    user_id: str,
    conversation_id: str,
    parsed: dict[str, str],
    raw_payload: dict[str, Any],
) -> MessageEnvelope:
    return MessageEnvelope(
        channel="sms",
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        body=parsed["body"],
        correlation_id=parsed["message_sid"],
        raw_payload=raw_payload,
    )


def format_sms_response(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= SMS_MAX_LENGTH:
        return cleaned
    return cleaned[: SMS_MAX_LENGTH - 3].rsplit(" ", 1)[0] + "..."


def build_twiml_response(text: str) -> str:
    response = MessagingResponse()
    response.message(format_sms_response(text))
    return str(response)