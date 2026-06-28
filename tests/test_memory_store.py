from danu.db.repositories.conversation import ConversationRepository
from danu.db.repositories.memory import MemoryRepository
from danu.memory.schemas import MemoryOp, MemoryOpType
from danu.memory.store import MemoryStore


def _create_conversation(session, tenant_id="default", user_id="user-1") -> str:
    repo = ConversationRepository(session)
    conversation = repo.create(tenant_id=tenant_id, user_id=user_id, channel="sms")
    return conversation.id


def test_inbound_event_persisted_before_any_outbound(session):
    store = MemoryStore(session)
    conversation_id = _create_conversation(session)

    inbound = store.append_inbound(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation_id,
        channel="sms",
        body="Hello",
        correlation_id="SM123",
    )

    assert inbound.event_type == "message.inbound"
    assert inbound.payload_json["content"] == "Hello"


def test_fast_track_memory_commits_immediately(session):
    store = MemoryStore(session)
    conversation_id = _create_conversation(session)

    proposed = store.stage_memory_ops(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation_id,
        ops=[
            MemoryOp(
                op_type=MemoryOpType.CREATE,
                category="instruction",
                key="timezone",
                value={"text": "America/New_York"},
                confidence=0.95,
                fast_track=True,
            )
        ],
    )

    memory_repo = MemoryRepository(session)
    item = memory_repo.get_current_item(tenant_id="default", user_id="user-1", key="timezone")
    assert item is not None
    assert item.value_json["text"] == "America/New_York"
    assert proposed.event_id


def test_memory_supersession_chain(session):
    store = MemoryStore(session)
    conversation_id = _create_conversation(session)

    first = store.stage_memory_ops(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation_id,
        ops=[
            MemoryOp(
                op_type=MemoryOpType.CREATE,
                category="preference",
                key="favorite_color",
                value={"color": "blue"},
                confidence=0.95,
                fast_track=True,
            )
        ],
    )

    second = store.stage_memory_ops(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation_id,
        ops=[
            MemoryOp(
                op_type=MemoryOpType.SUPERSEDE,
                category="preference",
                key="favorite_color",
                value={"color": "green"},
                confidence=0.95,
                fast_track=True,
            )
        ],
    )

    memory_repo = MemoryRepository(session)
    current = memory_repo.get_current_item(tenant_id="default", user_id="user-1", key="favorite_color")
    assert current is not None
    assert current.value_json["color"] == "green"
    assert first.event_id != second.event_id