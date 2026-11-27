# Mischief

Turn it on, pick a voice, and that voice is used in your messages, calls and games.

Mischief uses [VoiceStudio](https://github.com/debpalash/VoiceStudio) as its
voice engine and connects to other apps only through their official APIs or a
virtual microphone. The full plan is in the
[architecture doc](https://claude.ai/artifact/BpTr7gHbtqX1Q2KLKPvkno).

```
Your mic ──► live voice changer ──► virtual mic ──► games, Discord, Zoom, WhatsApp Desktop
Text / agent ──► VoiceStudio TTS ──► connectors ──► Telegram bot (more coming)
                      ▲
          consent gate + voice picker (one voice for everything)
```

## Status

| Part | State |
| --- | --- |
| Voice picker, on/off switch, consent gate | Working (`mischief` CLI) |
| Text to speech in your voice | Working, through VoiceStudio |
| Telegram voice-note bot | Working, official Bot API |
| Live voice into a virtual mic | Experimental: phrase by phrase, 1 to 3 s delay |
| Low-latency live voice | Planned (needs a real-time voice-conversion engine) |
| Discord bot, WhatsApp Business, social posting | Planned |
| Agent skill (CLI-Anything style) | `skills/mischief/SKILL.md` |
| Desktop app UI | Planned |

## Setup

1. Install and start [VoiceStudio](https://github.com/debpalash/VoiceStudio/releases/latest).
2. In VoiceStudio, clone **your own** voice, then record the ownership consent:
   Saved voices → Edit voice profile → Voice ownership. Or design a voice from a description.
3. Install Mischief (Python 3.10+):

   ```bash
   pip install -e .            # add [live] for the live voice prototype
   mischief voices
   mischief use "My voice"
   mischief on
   mischief say "Hello from my Mischief voice" -o hello.mp3
   ```

### Telegram bot

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Find your chat id (for example by messaging [@userinfobot](https://t.me/userinfobot)).
3. Run:

   ```bash
   export TELEGRAM_BOT_TOKEN=...            # never commit this
   export TELEGRAM_ALLOWED_CHAT_IDS=123456  # only these chats can use the bot
   mischief telegram
   ```

   Send the bot text and it replies with a voice note in your voice, captioned
   "AI voice", which you can forward to any chat.

### Live voice (experimental)

1. Install a virtual audio cable: VB-CABLE on Windows, BlackHole on macOS.
2. `pip install -e ".[live]"`, then `mischief live --list-devices`.
3. `mischief live --output "CABLE Input"` and pick **CABLE Output** as the
   microphone in Discord, Zoom, WhatsApp Desktop or your game.

This prototype converts each phrase after you finish it, so there is a delay.
It is good for testing; real-time conversion is the next phase.

## Consent and safety

- Only two kinds of voices can be used: a clone whose owner recorded
  VoiceStudio's consent statement, or a designed voice that imitates nobody.
  Other clones are hidden and refused everywhere in Mischief.
- Mischief is not for impersonating real people. Don't clone a voice from
  someone else's recordings.
- VoiceStudio watermarks all generated audio as synthetic; Mischief never removes it.
- Messages sent by connectors are labelled as AI voice by default.
- Connectors use official APIs only. Automating a personal WhatsApp, Instagram
  or Discord account breaks those platforms' terms and can get the account banned.

## Licences

Mischief talks to VoiceStudio over its local HTTP API and does not include its
code. VoiceStudio itself is AGPL-3.0, and its default OmniVoice model weights
are non-commercial (CC-BY-NC). If you plan to sell Mischief or bundle
VoiceStudio with it, check those terms or buy VoiceStudio's commercial licence.
Mischief's own licence is still to be chosen.

## Development

```bash
pip install -e ".[dev]"
pytest
```
