"""Consent gate: decides which VoiceStudio voices Mischief may use.

A voice is usable only when it imitates nobody (a *designed* voice) or when
its owner has recorded VoiceStudio's ownership consent statement
(Saved voices -> Edit voice profile -> Voice ownership). Clones of anyone else
never show up in Mischief, the same rule VoiceStudio applies to phone calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class Voice:
    id: str
    name: str
    kind: str  # "clone" or "design"
    verified_own_voice: bool
    consent_recorded_at: float | None = None

    @property
    def allowed(self) -> bool:
        return self.kind == "design" or self.verified_own_voice

    @property
    def reason(self) -> str:
        if self.kind == "design":
            return "designed voice (imitates nobody)"
        if self.verified_own_voice:
            return "clone with recorded owner consent"
        return "clone without recorded consent: verify ownership in VoiceStudio first"


def voice_from_profile(profile: Mapping[str, Any]) -> Voice:
    """Build a Voice from a VoiceStudio ``GET /profiles`` row."""
    # VoiceStudio treats a NULL kind as a legacy clone.
    kind = (profile.get("kind") or "clone").strip().lower()
    recorded = profile.get("consent_recorded_at")
    return Voice(
        id=str(profile["id"]),
        name=str(profile.get("name") or profile["id"]),
        kind=kind,
        verified_own_voice=bool(profile.get("verified_own_voice")),
        consent_recorded_at=float(recorded) if recorded else None,
    )


def split_voices(profiles: Iterable[Mapping[str, Any]]) -> tuple[list[Voice], list[Voice]]:
    """Return (allowed, blocked) voices from VoiceStudio profile rows."""
    allowed: list[Voice] = []
    blocked: list[Voice] = []
    for row in profiles:
        voice = voice_from_profile(row)
        (allowed if voice.allowed else blocked).append(voice)
    return allowed, blocked


class ConsentError(RuntimeError):
    """Raised when a voice without consent is about to be used."""


def require_allowed(voice: Voice) -> Voice:
    if not voice.allowed:
        raise ConsentError(
            f"Voice '{voice.name}' has no recorded owner consent. Record the consent "
            "statement in VoiceStudio (Saved voices -> Edit voice profile -> Voice "
            "ownership), or use a designed voice."
        )
    return voice
