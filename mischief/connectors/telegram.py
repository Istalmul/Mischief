"""Telegram connector: a bot that turns your text into voice notes in your chosen voice.

Uses the official Telegram Bot API (allowed by Telegram's terms). It does not
automate your personal Telegram account. Only chats you list in
``TELEGRAM_ALLOWED_CHAT_IDS`` can use the bot, so nobody else can make it
speak in your voice.

Usage in Telegram: send the bot any text (or ``/say text``). It replies with a
voice note in the active Mischief voice, which you can forward anywhere.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable

import requests

from ..engine import VoiceStudio
from ..state import State

API = "https://api.telegram.org"
AI_CAPTION = "AI voice (Mischief)"


def parse_allowed(raw: str | None) -> set[int]:
    ids: set[int] = set()
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip()
        if part:
            ids.add(int(part))
    return ids


class TelegramBot:
    def __init__(self, token: str, allowed_chats: set[int], engine: VoiceStudio | None = None,
                 http: requests.Session | None = None, caption: str | None = AI_CAPTION,
                 load_state: Callable[[], State] = State.load):
        if not allowed_chats:
            raise ValueError("Set TELEGRAM_ALLOWED_CHAT_IDS to your own chat id(s).")
        self.base = f"{API}/bot{token}"
        self.allowed = allowed_chats
        self.engine = engine or VoiceStudio()
        self.http = http or requests.Session()
        self.caption = caption
        self.load_state = load_state
        self.offset = 0

    def _api(self, method: str, **kw: Any) -> Any:
        resp = self.http.post(f"{self.base}/{method}", timeout=60, **kw)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method} failed: {body}")
        return body["result"]

    def reply_text(self, chat_id: int, text: str) -> None:
        self._api("sendMessage", data={"chat_id": chat_id, "text": text})

    def handle(self, update: dict[str, Any]) -> None:
        msg = update.get("message") or {}
        chat_id = (msg.get("chat") or {}).get("id")
        text = (msg.get("text") or "").strip()
        if chat_id is None or not text:
            return
        if chat_id not in self.allowed:
            return  # silently ignore strangers
        if text in ("/start", "/help"):
            self.reply_text(chat_id, "Send me text and I'll reply with a voice note in your Mischief voice.")
            return
        if text.startswith("/say"):
            text = text[4:].strip()
            if not text:
                return
        state = self.load_state()
        if not state.enabled or not state.voice_id:
            self.reply_text(chat_id, "Mischief is off or no voice is picked. Run `mischief use <voice>` and `mischief on`.")
            return
        voice = self.engine.find_voice(state.voice_id)
        audio = self.engine.speak(voice, text, output_format="opus_48000_64")
        data: dict[str, Any] = {"chat_id": chat_id}
        if self.caption:
            data["caption"] = self.caption
        self._api("sendVoice", data=data, files={"voice": ("voice.ogg", audio, "audio/ogg")})

    def poll_once(self) -> int:
        updates = self._api("getUpdates", data={"offset": self.offset, "timeout": 30})
        for update in updates:
            self.offset = max(self.offset, update["update_id"] + 1)
            try:
                self.handle(update)
            except Exception as exc:  # keep the bot alive; tell the owner
                chat_id = ((update.get("message") or {}).get("chat") or {}).get("id")
                if chat_id in self.allowed:
                    self.reply_text(chat_id, f"Couldn't make that voice note: {exc}")
        return len(updates)

    def run(self) -> None:
        while True:
            try:
                self.poll_once()
            except requests.RequestException:
                time.sleep(5)


def from_env() -> TelegramBot:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN (from @BotFather).")
    return TelegramBot(token, parse_allowed(os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS")))
