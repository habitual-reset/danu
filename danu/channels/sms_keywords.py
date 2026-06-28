from __future__ import annotations

STOP_KEYWORDS = frozenset({"STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"})
START_KEYWORDS = frozenset({"START", "YES", "UNSTOP"})
HELP_KEYWORDS = frozenset({"HELP", "INFO"})

OPT_OUT_MESSAGE = (
    "DANU: You have been unsubscribed and will no longer receive messages. "
    "Reply START to resubscribe. Msg & data rates may apply."
)
OPT_IN_MESSAGE = (
    "DANU: You're subscribed to the DANU personal AI assistant. "
    "Message frequency varies. Reply HELP for help. Reply STOP to opt out. "
    "Msg & data rates may apply."
)
HELP_MESSAGE = (
    "DANU: Personal AI assistant. Reply STOP to cancel SMS. "
    "Email journey@habitualreset.com for support. Msg & data rates may apply."
)
OPTED_OUT_NOTICE = (
    "DANU: You are opted out. Reply START to resubscribe. "
    "Msg & data rates may apply."
)


def normalize_sms_body(body: str) -> str:
    return body.strip().upper()


def classify_sms_keyword(body: str) -> str | None:
    keyword = normalize_sms_body(body)
    if keyword in STOP_KEYWORDS:
        return "stop"
    if keyword in START_KEYWORDS:
        return "start"
    if keyword in HELP_KEYWORDS:
        return "help"
    return None