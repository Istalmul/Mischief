"""The on/off switch and the chosen voice, shared by every Mischief feature."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("MISCHIEF_HOME") or Path.home() / ".mischief")


@dataclass
class State:
    enabled: bool = False
    voice_id: str | None = None
    voice_name: str | None = None

    @classmethod
    def load(cls) -> "State":
        path = home() / "state.json"
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            return cls()
        return cls(enabled=bool(data.get("enabled")), voice_id=data.get("voice_id"),
                   voice_name=data.get("voice_name"))

    def save(self) -> None:
        path = home() / "state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2))
        tmp.replace(path)
