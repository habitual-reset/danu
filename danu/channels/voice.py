from __future__ import annotations

from typing import Any

from twilio.twiml.voice_response import Gather, VoiceResponse

from danu.channels.base import MessageEnvelope

VOICE_MAX_CHARS = 280
POLLY_VOICE = "Polly.Joanna-Neural"
GATHER_KWARGS = {
    "input": "speech",
    "method": "POST",
    "speech_timeout": "auto",
    "language": "en-US",
    "speech_model": "phone_call",
}


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


def _append_gather(response: VoiceResponse, *, action_url: str) -> None:
    gather = Gather(action=action_url, **GATHER_KWARGS)
    response.append(gather)


def build_incoming_call_twiml(*, gather_action_url: str, status_callback_url: str | None = None) -> str:
    kwargs = {}
    if status_callback_url:
        kwargs["status_callback"] = status_callback_url
        kwargs["status_callback_event"] = "completed"
    response = VoiceResponse(**kwargs)
    response.say("Hey, it's DANU. What's up?", voice=POLLY_VOICE)
    _append_gather(response, action_url=gather_action_url)
    response.say("Didn't catch that. Bye.", voice=POLLY_VOICE)
    response.hangup()
    return str(response)


def build_gather_response_twiml(*, text: str, gather_action_url: str) -> str:
    response = VoiceResponse()
    response.say(format_voice_response(text), voice=POLLY_VOICE)
    _append_gather(response, action_url=gather_action_url)
    response.say("Talk later.", voice=POLLY_VOICE)
    response.hangup()
    return str(response)


def build_no_speech_twiml(*, gather_action_url: str) -> str:
    response = VoiceResponse()
    response.say("Sorry, missed that.", voice=POLLY_VOICE)
    _append_gather(response, action_url=gather_action_url)
    response.hangup()
    return str(response)