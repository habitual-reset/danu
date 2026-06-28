from __future__ import annotations

from danu.config import Settings


def should_validate_twilio_signature(settings: Settings) -> bool:
    """Validate signatures whenever an auth token is configured."""
    return bool(settings.twilio_auth_token.strip())


def validate_twilio_signature(url: str, params: dict, signature: str, auth_token: str) -> bool:
    if not auth_token:
        return False

    from twilio.request_validator import RequestValidator

    validator = RequestValidator(auth_token)
    return validator.validate(url, params, signature)


def compute_twilio_signature(url: str, params: dict, auth_token: str) -> str:
    """Generate a valid signature for tests and local tooling."""
    from twilio.request_validator import RequestValidator

    validator = RequestValidator(auth_token)
    return validator.compute_signature(url, params)