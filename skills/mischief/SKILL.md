---
name: "mischief"
description: >-
  Speak in the user's own chosen voice through the Mischief CLI: list consented voices, pick one,
  turn Mischief on or off, and render text to audio. Use when an agent should talk in the user's voice.
---

# mischief

Agent skill for the `mischief` CLI, written in the CLI-Anything harness style so
agents (Claude Code, Codex, OpenClaw and others) can drive Mischief the same way
they drive the `cli-anything-*` harnesses.

## Install

```bash
pip install -e .            # from the Mischief repo
```

Prerequisite: the VoiceStudio app or backend running locally (default
`http://127.0.0.1:3900`, or set `VOICESTUDIO_URL`).

## Commands

```bash
mischief status                      # on/off and the chosen voice
mischief voices                      # voices you may use (consented clones and designed voices)
mischief use "My voice"              # pick the voice used everywhere
mischief on | mischief off           # the master switch
mischief say "Running late" -o note.mp3
```

## Rules for agents

- Only use voices that `mischief voices` lists as usable. Never try to work
  around the consent gate or clone a voice from someone else's audio.
- Never use the voice to pretend to be a different real person, and keep the
  AI disclosure on anything sent to other people.
- Respect `mischief off`: if Mischief is off, do not speak in the user's voice.
