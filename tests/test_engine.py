import pytest

from conftest import FakeResponse, FakeSession
from mischief.consent import ConsentError, voice_from_profile
from mischief.engine import EngineError, VoiceStudio


def make(profiles, extra=None):
    routes = {("GET", "/profiles"): FakeResponse(json_body=profiles)}
    routes.update(extra or {})
    session = FakeSession(routes)
    return VoiceStudio(base_url="http://vs:3900", session=session), session


def test_find_voice_by_name_or_id(profiles):
    vs, _ = make(profiles)
    assert vs.find_voice("my voice").id == "me"
    assert vs.find_voice("robot").name == "Robot"


def test_find_voice_refuses_voice_without_consent(profiles):
    vs, _ = make(profiles)
    with pytest.raises(ConsentError):
        vs.find_voice("celeb")


def test_unknown_voice(profiles):
    vs, _ = make(profiles)
    with pytest.raises(EngineError):
        vs.find_voice("nobody")


def test_speak_uses_elevenlabs_route(profiles):
    vs, session = make(profiles, {("POST", "/elevenlabs/v1/text-to-speech/me"): FakeResponse(content=b"MP3")})
    assert vs.speak(vs.find_voice("me"), "hi") == b"MP3"
    method, url, kw = session.calls[-1]
    assert kw["json"]["text"] == "hi"
    assert kw["params"] == {"output_format": "mp3_44100_128"}


def test_speak_never_sends_unverified_voice(profiles):
    vs, session = make(profiles)
    with pytest.raises(ConsentError):
        vs.speak(voice_from_profile(profiles[2]), "hi")
    assert all("text-to-speech" not in url for _, url, _ in session.calls)


def test_api_key_is_sent_as_bearer(profiles):
    vs, session = make(profiles)
    vs.api_key = "k"
    vs.profiles()
    assert session.calls[-1][2]["headers"] == {"Authorization": "Bearer k"}


def test_http_error_becomes_engine_error(profiles):
    vs, _ = make(profiles, {("POST", "/elevenlabs/v1/text-to-speech/me"): FakeResponse(500, {"x": 1})})
    with pytest.raises(EngineError):
        vs.speak(vs.find_voice("me"), "hi")
