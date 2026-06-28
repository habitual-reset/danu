from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from danu.agent.orchestrator import AgentOrchestrator
from danu.api.deps import TwilioVoiceContext, get_app_settings, get_db, get_twilio_voice_context
from danu.channels.voice import (
    build_farewell_twiml,
    build_gather_response_twiml,
    build_hold_twiml,
    build_incoming_call_twiml,
    build_no_speech_twiml,
    build_still_working_twiml,
    build_voice_envelope,
    is_farewell,
    parse_twilio_voice,
)
from danu.config import Settings
from danu.db.repositories.conversation import ConversationRepository
from danu.db.repositories.voice_hold import VoiceHoldRepository
from danu.onboarding.service import OnboardingService
from danu.usage.tracker import UsageTracker
from danu.voice.work_detector import (
    classify_work_type,
    estimate_seconds,
    hold_message,
    needs_hold,
    still_working_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio"])


def _process_turn(
    *,
    session: Session,
    settings: Settings,
    voice: TwilioVoiceContext,
    conversation_id: str,
    speech_text: str,
    raw_payload: dict,
) -> str:
    orchestrator = AgentOrchestrator(session)
    envelope = build_voice_envelope(
        tenant_id=settings.default_tenant_id,
        user_id=voice.user_id,
        conversation_id=conversation_id,
        body=speech_text,
        parsed=parse_twilio_voice(raw_payload),
        raw_payload=raw_payload,
    )
    result = orchestrator.handle_turn(envelope)
    return result.response_text


@router.post("/voice")
async def incoming_voice(
    voice: TwilioVoiceContext = Depends(get_twilio_voice_context),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    orchestrator = AgentOrchestrator(session)
    orchestrator.resolve_conversation(
        tenant_id=settings.default_tenant_id,
        user_id=voice.user_id,
        channel="voice",
        correlation_id=voice.params.get("CallSid"),
    )

    onboarding = OnboardingService(session)
    greeting = onboarding.voice_greeting(
        tenant_id=settings.default_tenant_id,
        user_id=voice.user_id,
    )

    gather_url = settings.twilio_webhook_url_for("/webhooks/twilio/voice/gather")
    status_url = settings.twilio_webhook_url_for("/webhooks/twilio/voice/status")
    return Response(
        content=build_incoming_call_twiml(
            gather_action_url=gather_url,
            status_callback_url=status_url,
            greeting=greeting,
        ),
        media_type="application/xml",
    )


@router.post("/voice/gather")
async def voice_gather(
    voice: TwilioVoiceContext = Depends(get_twilio_voice_context),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    parsed = parse_twilio_voice(voice.params)
    gather_url = settings.twilio_webhook_url_for("/webhooks/twilio/voice/gather")
    work_url = settings.twilio_webhook_url_for("/webhooks/twilio/voice/work")

    if not parsed["speech_result"]:
        return Response(
            content=build_no_speech_twiml(gather_action_url=gather_url),
            media_type="application/xml",
        )

    orchestrator = AgentOrchestrator(session)
    conversation_id = orchestrator.resolve_conversation(
        tenant_id=settings.default_tenant_id,
        user_id=voice.user_id,
        channel="voice",
        correlation_id=parsed["call_sid"],
    )

    onboarding = OnboardingService(session)
    state = onboarding.load_state(
        tenant_id=settings.default_tenant_id,
        user_id=voice.user_id,
    )

    if is_farewell(parsed["speech_result"]):
        try:
            reply = _process_turn(
                session=session,
                settings=settings,
                voice=voice,
                conversation_id=conversation_id,
                speech_text=parsed["speech_result"],
                raw_payload=voice.params,
            )
        except Exception:
            logger.exception("Farewell turn failed")
            session.rollback()
            reply = "Talk soon."
        return Response(
            content=build_farewell_twiml(text=reply),
            media_type="application/xml",
        )

    use_hold = (
        settings.voice_hold_enabled
        and needs_hold(parsed["speech_result"], onboarding_complete=state.completed)
    )

    if use_hold:
        work_type = classify_work_type(parsed["speech_result"])
        estimated = estimate_seconds(parsed["speech_result"], work_type=work_type)
        holds = VoiceHoldRepository(session)
        holds.create(
            tenant_id=settings.default_tenant_id,
            user_id=voice.user_id,
            conversation_id=conversation_id,
            call_sid=parsed["call_sid"],
            speech_text=parsed["speech_result"],
            work_type=work_type,
            estimated_seconds=estimated,
        )
        message = hold_message(
            work_type=work_type,
            estimated_seconds=estimated,
            agent_name=state.display_agent_name,
            onboarding=not state.completed,
        )
        loops = max(1, estimated // 3)
        return Response(
            content=build_hold_twiml(
                message=message,
                music_url=settings.voice_hold_music_url,
                work_url=work_url,
                music_loops=loops,
                pause_seconds=estimated if not settings.voice_hold_music_url else 0,
            ),
            media_type="application/xml",
        )

    try:
        reply = _process_turn(
            session=session,
            settings=settings,
            voice=voice,
            conversation_id=conversation_id,
            speech_text=parsed["speech_result"],
            raw_payload=voice.params,
        )
    except Exception:
        logger.exception(
            "Voice turn failed for user=%s conversation=%s",
            voice.user_id,
            conversation_id,
        )
        session.rollback()
        reply = "Something went wrong. Please try again."

    return Response(
        content=build_gather_response_twiml(text=reply, gather_action_url=gather_url),
        media_type="application/xml",
    )


@router.api_route("/voice/work", methods=["GET", "POST"])
async def voice_work(
    voice: TwilioVoiceContext = Depends(get_twilio_voice_context),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    call_sid = voice.params.get("CallSid", "").strip()
    gather_url = settings.twilio_webhook_url_for("/webhooks/twilio/voice/gather")
    work_url = settings.twilio_webhook_url_for("/webhooks/twilio/voice/work")

    holds = VoiceHoldRepository(session)
    job = holds.get_active_for_call(call_sid)
    if job is None:
        latest = holds.get_latest_for_call(call_sid)
        if latest and latest.status == "done" and latest.response_text:
            reply = latest.response_text
            if is_farewell(latest.speech_text):
                return Response(
                    content=build_farewell_twiml(text=reply),
                    media_type="application/xml",
                )
            return Response(
                content=build_gather_response_twiml(text=reply, gather_action_url=gather_url),
                media_type="application/xml",
            )
        return Response(
            content=build_gather_response_twiml(
                text="Sorry, I lost track of that. What were you saying?",
                gather_action_url=gather_url,
            ),
            media_type="application/xml",
        )

    if job.status == "processing":
        onboarding = OnboardingService(session)
        state = onboarding.load_state(tenant_id=job.tenant_id, user_id=job.user_id)
        return Response(
            content=build_still_working_twiml(
                message=still_working_message(agent_name=state.display_agent_name),
                music_url=settings.voice_hold_music_url,
                work_url=work_url,
            ),
            media_type="application/xml",
        )

    holds.mark_processing(job)
    logger.info(
        "Processing hold job %s for call %s: %s",
        job.id,
        call_sid,
        job.speech_text[:80],
    )

    try:
        reply = _process_turn(
            session=session,
            settings=settings,
            voice=voice,
            conversation_id=job.conversation_id,
            speech_text=job.speech_text,
            raw_payload=voice.params,
        )
        holds.mark_done(job, response_text=reply)
    except Exception:
        logger.exception("Hold work failed for call=%s job=%s", call_sid, job.id)
        holds.mark_failed(job, response_text="Something went wrong. Please try again.")
        reply = "Something went wrong. Please try again."

    if is_farewell(job.speech_text):
        return Response(
            content=build_farewell_twiml(text=reply),
            media_type="application/xml",
        )

    return Response(
        content=build_gather_response_twiml(text=reply, gather_action_url=gather_url),
        media_type="application/xml",
    )


@router.post("/voice/status")
async def voice_status(
    voice: TwilioVoiceContext = Depends(get_twilio_voice_context),
    session: Session = Depends(get_db),
) -> Response:
    call_status = voice.params.get("CallStatus", "").strip().lower()
    call_sid = voice.params.get("CallSid", "").strip()

    if call_status != "completed" or not call_sid:
        return Response(status_code=204)

    conversations = ConversationRepository(session)
    conversation = conversations.get_by_correlation_id(call_sid)
    if conversation is None:
        return Response(status_code=204)

    duration_raw = voice.params.get("CallDuration", "0")
    try:
        duration_seconds = int(duration_raw)
    except ValueError:
        duration_seconds = 0

    UsageTracker(session).record_twilio_voice(
        tenant_id=conversation.tenant_id,
        user_id=conversation.user_id,
        duration_seconds=duration_seconds,
        conversation_id=conversation.id,
        call_sid=call_sid,
    )

    holds = VoiceHoldRepository(session)
    stale_job = holds.get_active_for_call(call_sid)
    if stale_job is not None:
        holds.mark_failed(stale_job, response_text="Call ended before hold work completed.")
        logger.warning("Hold job %s orphaned on hangup for call %s", stale_job.id, call_sid)

    orchestrator = AgentOrchestrator(session)
    orchestrator.close_conversation(conversation.id)
    logger.info(
        "Voice call completed (%ss); consolidation queued for %s",
        duration_seconds,
        conversation.id,
    )
    return Response(status_code=204)