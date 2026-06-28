import logging

from sqlalchemy.orm import Session

from danu.channels.outbound_sms import send_outbound_sms
from danu.db.models.task import Task
from danu.db.repositories.sms_subscription import SmsSubscriptionRepository
from danu.memory.consolidate import MemoryConsolidator

logger = logging.getLogger(__name__)


def handle_consolidate_memory(session: Session, task: Task) -> None:
    payload = task.payload_json
    consolidator = MemoryConsolidator(session)
    consolidator.consolidate_conversation(
        tenant_id=task.tenant_id,
        user_id=task.user_id or "",
        conversation_id=payload["conversation_id"],
    )
    if task.user_id:
        consolidator.process_proposed_events(
            tenant_id=task.tenant_id,
            user_id=task.user_id,
        )


def handle_send_sms_reminder(session: Session, task: Task) -> None:
    payload = task.payload_json
    phone = payload.get("phone_number", "")
    message = payload.get("message", "Reminder from DANU.")
    subscriptions = SmsSubscriptionRepository(session)

    if not subscriptions.is_opted_in(tenant_id=task.tenant_id, phone_number=phone):
        payload["delivery_status"] = "blocked_opt_out"
        task.payload_json = payload
        logger.warning("SMS reminder blocked: %s opted out", phone)
        return

    result = send_outbound_sms(to_number=phone, body=message)
    payload["delivery_status"] = "sent" if result.sent else result.blocked_reason
    payload["message_sid"] = result.sid
    task.payload_json = payload

    if result.sent:
        logger.info("SMS reminder sent to %s task=%s", phone, task.id)
    else:
        logger.warning(
            "SMS reminder queued-not-delivered task=%s reason=%s",
            task.id,
            result.blocked_reason,
        )


HANDLERS = {
    "consolidate_memory": handle_consolidate_memory,
    "send_sms_reminder": handle_send_sms_reminder,
}