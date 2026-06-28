from danu.db.repositories.conversation import ConversationRepository
from danu.memory.retrieve import MemoryRetriever
from danu.memory.schemas import MemoryOp, MemoryOpType
from danu.memory.store import MemoryStore


def test_retrieve_includes_system_facts_and_recent_messages(session):
    conversations = ConversationRepository(session)
    conversation = conversations.create(tenant_id="default", user_id="user-1", channel="sms")

    store = MemoryStore(session)
    store.stage_memory_ops(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation.id,
        ops=[
            MemoryOp(
                op_type=MemoryOpType.CREATE,
                category="instruction",
                key="greeting_style",
                value={"text": "be brief"},
                confidence=0.95,
                fast_track=True,
            )
        ],
    )

    store.append_inbound(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation.id,
        channel="sms",
        body="What's my greeting style?",
        correlation_id="SM1",
    )

    retriever = MemoryRetriever(session)
    pack = retriever.retrieve(
        tenant_id="default",
        user_id="user-1",
        conversation_id=conversation.id,
        query="greeting style",
    )

    assert any(fact.key == "greeting_style" for fact in pack.system_facts)
    assert pack.recent_messages
    assert pack.recent_messages[-1].content == "What's my greeting style?"