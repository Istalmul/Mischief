import queue
import wave
import io

import numpy as np

from conftest import FakeResponse, FakeSession
from mischief import cli, live
from mischief.state import State


def run(argv, profiles, monkeypatch):
    session = FakeSession({("GET", "/profiles"): FakeResponse(json_body=profiles)})
    real = cli.VoiceStudio
    monkeypatch.setattr(cli, "VoiceStudio", lambda base_url=None, **_: real(base_url="http://vs", session=session))
    return cli.main(argv)


def test_use_then_on(profiles, monkeypatch, capsys):
    assert run(["on"], profiles, monkeypatch) == 1  # no voice yet
    assert run(["use", "My voice"], profiles, monkeypatch) == 0
    assert run(["on"], profiles, monkeypatch) == 0
    state = State.load()
    assert state.enabled and state.voice_id == "me"


def test_use_refuses_unverified_clone(profiles, monkeypatch, capsys):
    assert run(["use", "celeb"], profiles, monkeypatch) == 1
    assert "consent" in capsys.readouterr().err
    assert State.load().voice_id is None


def test_voices_lists_blocked_separately(profiles, monkeypatch, capsys):
    run(["voices"], profiles, monkeypatch)
    out = capsys.readouterr().out
    assert out.index("My voice") < out.index("Hidden") < out.index("Someone else")


def test_split_phrases_cuts_at_pauses():
    q = queue.Queue()
    loud = np.full(live.BLOCK, 0.2, dtype="float32")
    quiet = np.zeros(live.BLOCK, dtype="float32")
    for block in [quiet] * 5 + [loud] * 3 + [quiet] * live.END_SILENCE_BLOCKS + [loud] * 2 + [quiet] * live.END_SILENCE_BLOCKS:
        q.put(block)
    q.put(None)
    phrases = list(live.split_phrases(np, q))
    assert len(phrases) == 2
    assert len(phrases[0]) == (3 + live.END_SILENCE_BLOCKS) * live.BLOCK


def test_to_wav_is_valid():
    data = live.to_wav(np, np.zeros(480, dtype="float32"))
    with wave.open(io.BytesIO(data)) as w:
        assert w.getframerate() == live.RATE and w.getnframes() == 480
