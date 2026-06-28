from danu.channels.sms_keywords import classify_sms_keyword


def test_classify_stop_variants():
    assert classify_sms_keyword("stop") == "stop"
    assert classify_sms_keyword("STOPALL") == "stop"
    assert classify_sms_keyword(" unsubscribe ") == "stop"


def test_classify_start_variants():
    assert classify_sms_keyword("start") == "start"
    assert classify_sms_keyword("YES") == "start"
    assert classify_sms_keyword("unstop") == "start"


def test_classify_help():
    assert classify_sms_keyword("help") == "help"
    assert classify_sms_keyword("INFO") == "help"


def test_non_keyword_returns_none():
    assert classify_sms_keyword("what's the weather") is None