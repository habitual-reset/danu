from __future__ import annotations

from dataclasses import dataclass

from danu.config import get_settings


@dataclass
class SmsDeliveryResult:
    sent: bool
    sid: str | None = None
    blocked_reason: str | None = None


def send_outbound_sms(*, to_number: str, body: str) -> SmsDeliveryResult:
    settings = get_settings()
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return SmsDeliveryResult(sent=False, blocked_reason="twilio_not_configured")
    if not settings.twilio_phone_number:
        return SmsDeliveryResult(sent=False, blocked_reason="twilio_number_missing")

    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        message = client.messages.create(
            to=to_number,
            from_=settings.twilio_phone_number,
            body=body,
        )
        return SmsDeliveryResult(sent=True, sid=message.sid)
    except Exception as exc:
        error = str(exc).lower()
        if "unverified" in error or "21610" in error or "a2p" in error or "30034" in error:
            return SmsDeliveryResult(sent=False, blocked_reason="a2p_or_carrier_blocked")
        return SmsDeliveryResult(sent=False, blocked_reason=f"twilio_error:{exc}")