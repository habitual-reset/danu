from danu.channels.sms import build_twiml_response, format_sms_response, parse_twilio_sms
from danu.channels.voice import (
    build_farewell_twiml,
    build_gather_response_twiml,
    build_incoming_call_twiml,
    format_voice_response,
)


def test_parse_twilio_sms_extracts_fields():
    parsed = parse_twilio_sms(
        {
            "From": "+15555550100",
            "To": "+15555550200",
            "Body": "Hello there",
            "MessageSid": "SM123",
        }
    )
    assert parsed["from_number"] == "+15555550100"
    assert parsed["body"] == "Hello there"
    assert parsed["message_sid"] == "SM123"


def test_format_sms_response_truncates_long_messages():
    text = "word " * 500
    formatted = format_sms_response(text)
    assert len(formatted) <= 1600


def test_build_twiml_response_wraps_message():
    twiml = build_twiml_response("Hi Matt")
    assert "<Message>" in twiml
    assert "Hi Matt" in twiml


def test_format_voice_response_truncates_long_replies():
    text = "word " * 200
    formatted = format_voice_response(text)
    assert len(formatted) <= 280


def test_incoming_voice_twiml_uses_neural_voice_and_status_callback():
    twiml = build_incoming_call_twiml(
        gather_action_url="/webhooks/twilio/voice/gather",
        status_callback_url="/webhooks/twilio/voice/status",
    )
    assert "Polly.Joanna-Neural" in twiml
    assert 'statusCallback="/webhooks/twilio/voice/status"' in twiml
    assert 'speechModel="phone_call"' in twiml


def test_gather_response_twiml_keeps_silent_gather():
    twiml = build_gather_response_twiml(
        text="Got it.",
        gather_action_url="/webhooks/twilio/voice/gather",
    )
    assert "Got it." in twiml
    assert "Anything else" not in twiml
    assert "Talk later" not in twiml


def test_farewell_twiml_hangs_up():
    twiml = build_farewell_twiml(text="Talk soon!")
    assert "Talk soon!" in twiml
    assert "<Hangup" in twiml