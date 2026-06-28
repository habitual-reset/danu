from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from danu.agent.orchestrator import AgentOrchestrator
from danu.api.deps import TwilioSmsContext, get_app_settings, get_db, get_twilio_sms_context
from danu.channels.sms import build_sms_envelope, build_twiml_response, parse_twilio_sms
from danu.channels.sms_keywords import (
    HELP_MESSAGE,
    OPTED_OUT_NOTICE,
    OPT_IN_MESSAGE,
    OPT_OUT_MESSAGE,
    classify_sms_keyword,
)
from danu.config import Settings
from danu.db.repositories.sms_subscription import SmsSubscriptionRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio"])


@router.post("/sms")
async def inbound_sms(
    sms: TwilioSmsContext = Depends(get_twilio_sms_context),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    parsed = parse_twilio_sms(sms.params)
    subscriptions = SmsSubscriptionRepository(session)

    if not parsed["body"]:
        return Response(
            content=build_twiml_response("I didn't catch a message. Try sending some text."),
            media_type="application/xml",
        )

    keyword = classify_sms_keyword(parsed["body"])
    if keyword == "stop":
        subscriptions.set_status(
            tenant_id=settings.default_tenant_id,
            phone_number=sms.from_number,
            status="opted_out",
        )
        return Response(content=build_twiml_response(OPT_OUT_MESSAGE), media_type="application/xml")

    if keyword == "start":
        subscriptions.set_status(
            tenant_id=settings.default_tenant_id,
            phone_number=sms.from_number,
            status="opted_in",
        )
        return Response(content=build_twiml_response(OPT_IN_MESSAGE), media_type="application/xml")

    if keyword == "help":
        return Response(content=build_twiml_response(HELP_MESSAGE), media_type="application/xml")

    if not subscriptions.is_opted_in(
        tenant_id=settings.default_tenant_id,
        phone_number=sms.from_number,
    ):
        return Response(content=build_twiml_response(OPTED_OUT_NOTICE), media_type="application/xml")

    orchestrator = AgentOrchestrator(session)
    conversation_id = orchestrator.resolve_conversation(
        tenant_id=settings.default_tenant_id,
        user_id=sms.user_id,
        channel="sms",
    )

    envelope = build_sms_envelope(
        tenant_id=settings.default_tenant_id,
        user_id=sms.user_id,
        conversation_id=conversation_id,
        parsed=parsed,
        raw_payload=sms.params,
    )

    try:
        result = orchestrator.handle_turn(envelope)
        reply = result.response_text
    except Exception:
        logger.exception(
            "SMS turn failed for user=%s conversation=%s",
            sms.user_id,
            conversation_id,
        )
        session.rollback()
        reply = "Something went wrong on my end. Please try again in a moment."

    return Response(content=build_twiml_response(reply), media_type="application/xml")