"""`mischief` command line: turn the app on, pick a voice, and use it everywhere."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .consent import ConsentError
from .engine import EngineError, VoiceStudio
from .state import State


def cmd_status(args, engine: VoiceStudio) -> int:
    state = State.load()
    print(f"Mischief is {'ON' if state.enabled else 'OFF'}")
    print(f"Voice: {state.voice_name or '(none picked)'}")
    print(f"VoiceStudio: {engine.base_url}")
    return 0


def cmd_voices(args, engine: VoiceStudio) -> int:
    allowed, blocked = engine.voices()
    active = State.load().voice_id
    print("Voices you can use:")
    for v in allowed or []:
        mark = "*" if v.id == active else " "
        print(f" {mark} {v.name}  [{v.id}]  {v.reason}")
    if not allowed:
        print("   none yet. Clone your own voice in VoiceStudio and record the ownership consent,")
        print("   or design a voice from a description.")
    if blocked:
        print("\nHidden until their owner records consent in VoiceStudio:")
        for v in blocked:
            print(f"   {v.name}  [{v.id}]")
    return 0


def cmd_use(args, engine: VoiceStudio) -> int:
    voice = engine.find_voice(args.voice)
    state = State.load()
    state.voice_id, state.voice_name = voice.id, voice.name
    state.save()
    print(f"Voice set to '{voice.name}' ({voice.reason}).")
    return 0


def cmd_switch(args, engine: VoiceStudio) -> int:
    state = State.load()
    if args.cmd == "on" and not state.voice_id:
        print("Pick a voice first: mischief voices, then mischief use <voice>.", file=sys.stderr)
        return 1
    state.enabled = args.cmd == "on"
    state.save()
    return cmd_status(args, engine)


def cmd_say(args, engine: VoiceStudio) -> int:
    state = State.load()
    if not state.voice_id:
        print("Pick a voice first: mischief use <voice>.", file=sys.stderr)
        return 1
    voice = engine.find_voice(state.voice_id)
    out = Path(args.out)
    fmt = "wav_44100" if out.suffix.lower() == ".wav" else "mp3_44100_128"
    out.write_bytes(engine.speak(voice, args.text, output_format=fmt))
    print(f"Saved {out} in '{voice.name}'. It carries VoiceStudio's AI watermark.")
    return 0


def cmd_live(args, engine: VoiceStudio) -> int:
    from . import live
    if args.list_devices:
        print(live.list_devices())
        return 0
    if args.output is None:
        print("Pass --output with your virtual cable (see --list-devices).", file=sys.stderr)
        return 1
    live.run(output=_device(args.output), input_device=_device(args.input), engine=engine)
    return 0


def cmd_telegram(args, engine: VoiceStudio) -> int:
    from .connectors import telegram
    bot = telegram.from_env()
    bot.engine = engine
    print("Telegram bot running. Press Ctrl+C to stop.")
    try:
        bot.run()
    except KeyboardInterrupt:
        pass
    return 0


def _device(value):
    if value is None:
        return None
    return int(value) if str(value).isdigit() else value


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mischief", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--voicestudio-url", help="VoiceStudio backend URL (default http://127.0.0.1:3900)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="show on/off and the chosen voice").set_defaults(fn=cmd_status)
    sub.add_parser("voices", help="list voices you are allowed to use").set_defaults(fn=cmd_voices)
    s = sub.add_parser("use", help="pick the voice to use everywhere")
    s.add_argument("voice", help="voice name or id")
    s.set_defaults(fn=cmd_use)
    sub.add_parser("on", help="turn Mischief on").set_defaults(fn=cmd_switch)
    sub.add_parser("off", help="turn Mischief off").set_defaults(fn=cmd_switch)
    s = sub.add_parser("say", help="speak text in your voice to an audio file")
    s.add_argument("text")
    s.add_argument("-o", "--out", default="mischief.mp3")
    s.set_defaults(fn=cmd_say)
    s = sub.add_parser("live", help="EXPERIMENTAL: your mic in your chosen voice, into a virtual mic")
    s.add_argument("--output", help="virtual cable device name or number")
    s.add_argument("--input", help="real microphone device (default: system default)")
    s.add_argument("--list-devices", action="store_true")
    s.set_defaults(fn=cmd_live)
    sub.add_parser("telegram", help="run the Telegram voice-note bot").set_defaults(fn=cmd_telegram)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine = VoiceStudio(base_url=args.voicestudio_url)
    try:
        return args.fn(args, engine)
    except (EngineError, ConsentError) as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
