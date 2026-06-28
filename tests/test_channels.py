from danu.channels.sms import build_twiml_response, format_sms_response, parse_twilio_sms


def test_parse_twilio_sms_extracts_fields():
    parsed = parse_twilio_sms(
        {
            "From": "+18143273565",
            "To": "+15551234567",
            "Body": "Hello there",
            "MessageSid": "SM123",
        }
    )
    assert parsed["from_number"] == "+18143273565"
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