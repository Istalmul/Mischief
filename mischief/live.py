"""EXPERIMENTAL live voice: mic -> your chosen voice -> a virtual microphone.

How it works: Mischief listens to your real mic, cuts your speech into
phrases at pauses, sends each phrase to VoiceStudio's speech-to-speech route,
and plays the result into a virtual audio cable. In Discord, Zoom, WhatsApp
Desktop or a game, pick that cable as the microphone.

Honest limits of this prototype: it works phrase by phrase, so the other side
hears each phrase after you finish it (typically 1 to 3 seconds of delay,
more without a GPU). True low-latency streaming conversion is Phase 2 of the
plan and needs a dedicated real-time voice-conversion engine.

Virtual cable drivers (install one, then pick it with --output):
- Windows: VB-CABLE (https://vb-audio.com/Cable/), output device "CABLE Input"
- macOS:   BlackHole 2ch (https://existential.audio/blackhole/)
- Linux:   a PulseAudio/PipeWire null sink

Needs the optional extras: pip install "mischief[live]"
"""

from __future__ import annotations

import io
import queue
import wave
from typing import Any

from .engine import VoiceStudio
from .state import State

RATE = 48000
BLOCK = 960  # 20 ms
SILENCE_RMS = 0.012  # below this a block counts as silence
END_SILENCE_BLOCKS = 20  # 400 ms of silence ends a phrase
MAX_PHRASE_BLOCKS = 50 * 8  # cut phrases at 8 seconds


def _deps() -> tuple[Any, Any]:
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as exc:  # pragma: no cover - depends on the machine
        raise SystemExit('Live voice needs extras: pip install "mischief[live]"') from exc
    return np, sd


def list_devices() -> str:
    _, sd = _deps()
    return str(sd.query_devices())


def to_wav(np: Any, samples: Any, rate: int = RATE) -> bytes:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def split_phrases(np: Any, blocks: "queue.Queue[Any]"):
    """Yield phrases (arrays) from a queue of mic blocks, split at pauses."""
    phrase: list[Any] = []
    quiet = 0
    while True:
        block = blocks.get()
        if block is None:
            break
        loud = float(np.sqrt(np.mean(block ** 2))) >= SILENCE_RMS
        if loud or phrase:
            phrase.append(block)
        quiet = 0 if loud else quiet + 1
        if phrase and (quiet >= END_SILENCE_BLOCKS or len(phrase) >= MAX_PHRASE_BLOCKS):
            yield np.concatenate(phrase)
            phrase, quiet = [], 0


def run(output: str | int, input_device: str | int | None = None,
        engine: VoiceStudio | None = None) -> None:  # pragma: no cover - needs audio hardware
    np, sd = _deps()
    state = State.load()
    if not state.enabled or not state.voice_id:
        raise SystemExit("Mischief is off or no voice is picked. Run `mischief use <voice>` and `mischief on`.")
    engine = engine or VoiceStudio()
    voice = engine.find_voice(state.voice_id)

    blocks: "queue.Queue[Any]" = queue.Queue()

    def on_audio(indata, frames, time_info, status):
        blocks.put(indata[:, 0].copy())

    print(f"*** LIVE VOICE ON: speaking as '{voice.name}'. Press Ctrl+C to stop. ***")
    with sd.InputStream(device=input_device, channels=1, samplerate=RATE, blocksize=BLOCK,
                        dtype="float32", callback=on_audio), \
         sd.RawOutputStream(device=output, channels=1, samplerate=RATE, dtype="int16") as out:
        try:
            for phrase in split_phrases(np, blocks):
                pcm = engine.convert(voice, to_wav(np, phrase), output_format="pcm_48000")
                out.write(pcm)
        except KeyboardInterrupt:
            pass
    print("*** LIVE VOICE OFF ***")
