from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ChannelType = Literal["sms", "voice"]


@dataclass
class MessageEnvelope:
    channel: ChannelType
    tenant_id: str
    user_id: str
    conversation_id: str
    body: str
    correlation_id: str
    raw_payload: dict[str, Any] = field(default_factory=dict)