import pytest

from conftest import FakeResponse, FakeSession
from mischief.connectors.telegram import TelegramBot, parse_allowed
from mischief.engine import VoiceStudio
from mischief.state import State


def tg_session():
    ok = FakeResponse(json_body={"ok": True, "result": {}})
    return FakeSession({("POST", "/sendMessage"): ok, ("POST", "/sendVoice"): ok})


def make_bot(profiles, state):
    vs = VoiceStudio(base_url="http://vs", session=FakeSession({
        ("GET", "/profiles"): FakeResponse(json_body=profiles),
        ("POST", "/elevenlabs/v1/text-to-speech/me"): FakeResponse(content=b"OGG"),
    }))
    tg = tg_session()
    bot = TelegramBot("T", {42}, engine=vs, http=tg, load_state=lambda: state)
    return bot, tg


def update(chat, text):
    return {"update_id": 1, "message": {"chat": {"id": chat}, "text": text}}


def test_parse_allowed():
    assert parse_allowed("1, 2;3") == {1, 2, 3}
    assert parse_allowed(None) == set()


def test_requires_allowlist():
    with pytest.raises(ValueError):
        TelegramBot("T", set())


def test_strangers_are_ignored(profiles):
    bot, tg = make_bot(profiles, State(enabled=True, voice_id="me"))
    bot.handle(update(7, "hello"))
    assert tg.calls == []


def test_owner_gets_voice_note_with_ai_caption(profiles):
    bot, tg = make_bot(profiles, State(enabled=True, voice_id="me"))
    bot.handle(update(42, "/say hello there"))
    method, url, kw = tg.calls[-1]
    assert url.endswith("/sendVoice")
    assert kw["files"]["voice"][1] == b"OGG"
    assert kw["data"]["caption"]


def test_off_switch_is_respected(profiles):
    bot, tg = make_bot(profiles, State(enabled=False, voice_id="me"))
    bot.handle(update(42, "hello"))
    assert tg.calls[-1][1].endswith("/sendMessage")
