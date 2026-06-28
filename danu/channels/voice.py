from __future__ import annotations

from typing import Any

from twilio.twiml.voice_response import Gather, VoiceResponse

from danu.channels.base import MessageEnvelope

VOICE_MAX_CHARS = 500


def parse_twilio_voice(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "from_number": payload.get("From", "").strip(),
        "to_number": payload.get("To", "").strip(),
        "call_sid": payload.get("CallSid", "").strip(),
        "speech_result": payload.get("SpeechResult", "").strip(),
        "confidence": payload.get("Confidence", "").strip(),
    }


def build_voice_envelope(
    *,
    tenant_id: str,
    user_id: str,
    conversation_id: str,
    body: str,
    parsed: dict[str, str],
    raw_payload: dict[str, Any],
) -> MessageEnvelope:
    return MessageEnvelope(
        channel="voice",
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        body=body,
        correlation_id=parsed["call_sid"],
        raw_payload=raw_payload,
    )


def format_voice_response(text: str, max_chars: int = VOICE_MAX_CHARS) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rsplit(" ", 1)[0] + "..."


def build_incoming_call_twiml(*, gather_action_url: str) -> str:
    response = VoiceResponse()
    response.say("Hi. I'm your assistant. What can I help with?", voice="Polly.Joanna")
    gather = Gather(
        input="speech",
        action=gather_action_url,
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say("I'm listening.", voice="Polly.Joanna")
    response.append(gather)
    response.say("I didn't hear anything. Goodbye.", voice="Polly.Joanna")
    response.hangup()
    return str(response)


def build_gather_response_twiml(*, text: str, gather_action_url: str) -> str:
    response = VoiceResponse()
    response.say(format_voice_response(text), voice="Polly.Joanna")
    gather = Gather(
        input="speech",
        action=gather_action_url,
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say("Anything else?", voice="Polly.Joanna")
    response.append(gather)
    response.say("Okay, talk later.", voice="Polly.Joanna")
    response.hangup()
    return str(response)


def build_no_speech_twiml(*, gather_action_url: str) -> str:
    response = VoiceResponse()
    response.say("Sorry, I didn't catch that.", voice="Polly.Joanna")
    gather = Gather(
        input="speech",
        action=gather_action_url,
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say("Try again.", voice="Polly.Joanna")
    response.append(gather)
    response.hangup()
    return str(response)