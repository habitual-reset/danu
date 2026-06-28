from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from danu.db.models.base import utcnow
from danu.db.models.voice_hold_job import VoiceHoldJob


class VoiceHoldRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        call_sid: str,
        speech_text: str,
        work_type: str,
        estimated_seconds: int,
    ) -> VoiceHoldJob:
        row = VoiceHoldJob(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            call_sid=call_sid,
            speech_text=speech_text,
            status="queued",
            work_type=work_type,
            estimated_seconds=estimated_seconds,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get_active_for_call(self, call_sid: str) -> VoiceHoldJob | None:
        stmt = (
            select(VoiceHoldJob)
            .where(
                VoiceHoldJob.call_sid == call_sid,
                VoiceHoldJob.status.in_(("queued", "processing")),
            )
            .order_by(VoiceHoldJob.created_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def get_latest_for_call(self, call_sid: str) -> VoiceHoldJob | None:
        stmt = (
            select(VoiceHoldJob)
            .where(VoiceHoldJob.call_sid == call_sid)
            .order_by(VoiceHoldJob.created_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def mark_processing(self, job: VoiceHoldJob) -> None:
        job.status = "processing"
        self.session.flush()

    def mark_done(self, job: VoiceHoldJob, *, response_text: str) -> None:
        job.status = "done"
        job.response_text = response_text
        job.completed_at = utcnow()
        self.session.flush()

    def mark_failed(self, job: VoiceHoldJob, *, response_text: str) -> None:
        job.status = "failed"
        job.response_text = response_text
        job.completed_at = utcnow()
        self.session.flush()