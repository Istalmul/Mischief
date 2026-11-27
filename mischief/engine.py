"""Client for the local VoiceStudio backend, Mischief's voice engine.

Mischief does not copy VoiceStudio's code. It runs VoiceStudio unchanged as a
separate local service and talks to it over HTTP, using:

- ``GET /profiles`` for saved voices and their consent state, and
- the ElevenLabs-compatible routes under ``/elevenlabs`` for speech.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from .consent import Voice, require_allowed, split_voices

DEFAULT_URL = "http://127.0.0.1:3900"
DEFAULT_MODEL = "eleven_multilingual_v2"  # maps to VoiceStudio's active engine


class EngineError(RuntimeError):
    pass


class VoiceStudio:
    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 session: requests.Session | None = None, timeout: float = 120.0):
        self.base_url = (base_url or os.environ.get("VOICESTUDIO_URL") or DEFAULT_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("VOICESTUDIO_API_KEY")
        self.http = session or requests.Session()
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        # Same-machine requests need no key; a remote backend does.
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def _call(self, method: str, path: str, **kw: Any) -> requests.Response:
        try:
            resp = self.http.request(method, self.base_url + path, headers=self._headers(),
                                     timeout=self.timeout, **kw)
        except requests.ConnectionError as exc:
            raise EngineError(
                f"Can't reach VoiceStudio at {self.base_url}. Start the VoiceStudio app "
                "or backend, or set VOICESTUDIO_URL."
            ) from exc
        if resp.status_code >= 400:
            raise EngineError(f"VoiceStudio {method} {path} failed: {resp.status_code} {resp.text[:300]}")
        return resp

    # Voices -------------------------------------------------------------
    def profiles(self) -> list[dict[str, Any]]:
        return self._call("GET", "/profiles").json()

    def voices(self) -> tuple[list[Voice], list[Voice]]:
        """(allowed, blocked) voices after the consent gate."""
        return split_voices(self.profiles())

    def find_voice(self, id_or_name: str) -> Voice:
        allowed, blocked = self.voices()
        needle = id_or_name.strip().lower()
        for voice in allowed + blocked:
            if voice.id.lower() == needle or voice.name.lower() == needle:
                return require_allowed(voice)
        raise EngineError(f"No VoiceStudio voice called '{id_or_name}'.")

    # Speech -------------------------------------------------------------
    def speak(self, voice: Voice, text: str, output_format: str = "mp3_44100_128") -> bytes:
        """Text to speech in ``voice``. Audio carries VoiceStudio's AI watermark."""
        require_allowed(voice)
        resp = self._call(
            "POST", f"/elevenlabs/v1/text-to-speech/{voice.id}",
            params={"output_format": output_format},
            json={"text": text, "model_id": DEFAULT_MODEL},
        )
        return resp.content

    def convert(self, voice: Voice, audio: bytes, filename: str = "input.wav",
                output_format: str = "pcm_48000") -> bytes:
        """Speech to speech: say recorded audio in ``voice``, keeping its delivery."""
        require_allowed(voice)
        resp = self._call(
            "POST", f"/elevenlabs/v1/speech-to-speech/{voice.id}",
            params={"output_format": output_format},
            files={"audio": (filename, audio, "audio/wav")},
            data={"model_id": DEFAULT_MODEL},
        )
        # Without a voice-conversion engine VoiceStudio transcribes and re-speaks
        # the clip instead (header X-OmniVoice-Fallback: respoken).
        return resp.content
