# TidalCycles Music Mode — Design Spec

**Date:** 2026-03-11
**Status:** Draft
**Author:** Troy + Claude

## Problem

Troy wants to make music by describing what he wants in plain English — "give me a 4 on the floor house beat" — and have the system translate that into live-coded TidalCycles patterns. Currently this requires learning Haskell-like Tidal syntax, keeping a GHCi session alive manually, and context-switching between a text editor and SuperCollider. The friction kills the creative flow.

## Solution

A **Music Mode** integrated into the Command Centre TUI. Press `m` to enter a natural-language-to-music coding environment. Claude translates plain English into TidalCycles code, manages the GHCi subprocess, and sends patterns to SuperDirt/SuperCollider. A song system tracks sessions with sequential IDs and auto-generated names.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Entry point | `m` key (dedicated) | Not part of `v` cycle — music is a mode, not a view |
| Module location | `brain/music/` | Isolated from CC core — only imported on activation |
| Loading strategy | Lazy import on `m` press | Zero cost when not using music mode |
| NL translation | Claude API via existing client | Reuses `brain/core/claude_client.py`, no new deps |
| Code confirmation | Show before send | User confirms (Enter), edits (e), or cancels (x) |
| Pattern storage | YAML files | Grep-friendly, consistent with rest of system |
| Song IDs | MUS-XXX sequential | Same pattern as OUT-XXX work items |
| Visualiser | Pure HTML/JS/Canvas | No build step, opens in Chrome via `v` key |
| Install | One-shot `install.sh` | Handles all deps: SuperCollider, Haskell, Tidal, SuperDirt |
## Folder Structure

```
brain/music/
├── __init__.py          # lazy-load guard — only imports submodules when called
├── tidal_bridge.py      # subprocess management for GHCi + TidalCycles
├── translator.py        # Claude API: natural language → Tidal code
├── song_manager.py      # creates/loads songs with sequential MUS-XXX IDs
├── visualiser/
│   └── index.html       # Chrome audio visualiser (Web Audio API)
├── patterns/
│   ├── drums/           # reusable drum pattern YAMLs
│   ├── bass/            # reusable bass line YAMLs
│   └── synth/           # reusable synth line YAMLs
├── songs/               # MUS-001-name/ folders with song.yml + session.tidal
├── samples/             # gitignored, custom audio samples
└── setup/
    └── install.sh       # one-shot installer for SuperCollider + Haskell + Tidal
```

## Song System

### IDs and Names

- IDs: `MUS-001`, `MUS-002`, etc. (sequential, zero-padded to 3 digits)
- Names: auto-generated fun/weird combos — `velvet-thunderclap`, `neon-platypus`, `cosmic-wombat`
- Folder: `brain/music/songs/MUS-001-velvet-thunderclap/`
### Song Metadata (`song.yml`)

```yaml
id: MUS-001
name: velvet-thunderclap
created: "2026-03-11T14:30:00"
bpm: 128
key: Am
genre: house
tags: [dark, driving, 4otf]
patterns_used:
  - drums/four-on-the-floor
  - bass/acid-303
notes: "Started as a simple house beat, evolved into acid territory"
```

### Session File (`session.tidal`)

Raw TidalCycles code from the session — everything that was sent to GHCi, in order. Acts as a replay log.

## CC Integration

### Entering Music Mode

- `m` key from any CC view enters music mode
- `Escape` exits back to previous view
- `/music` slash command also enters music mode from command bar
- Music mode is **not** part of the `v` cycle (Stream → Grid → Diagram) — it's a dedicated mode
### Layout (Three Panels)

```
┌─────────────────────────────┬──────────────────┐
│                             │                  │
│   Pattern Monitor           │  Active Patterns │
│   (live Tidal code)         │                  │
│                             │  d1: kick snare  │
│   d1 $ s "bd sn bd sn"     │  d2: hihat       │
│   d2 $ s "hh*8"            │  d3: bass (muted)│
│   d3 $ silence              │                  │
│                             │  BPM: 128        │
│                             │  Key: Am         │
│                             │                  │
├─────────────────────────────┴──────────────────┤
│ ♪ describe what you want...                     │
└─────────────────────────────────────────────────┘
```

- **Pattern Monitor** (~70% width): shows current Tidal code, syntax-highlighted
- **Active Patterns** (~30% width): sidebar listing active orbit/pattern names, mute state
- **Chat Input** (bottom): natural language input field

### Status Bar

```
♪ MUS-003-cosmic-wombat | 128 BPM | Am | ▶ playing | d1 d2 d3 active
```

When no song loaded:
```
♪ no song | — BPM | — | ■ stopped
```
### Music Mode Keys

| Key | Action |
|-----|--------|
| `v` | Open visualiser in Chrome |
| `s` | Save current session |
| `h` | Hush — silence all patterns immediately |
| `n` | New song (auto-generates ID + name) |
| `p` | Browse saved patterns |
| `+` / `-` | Increase / decrease BPM by 5 |
| `Shift+` / `Shift-` | Increase / decrease BPM by 1 |
| `Escape` | Exit music mode (patterns keep playing) |

## Tidal Bridge (`tidal_bridge.py`)

### Subprocess Management

- Spawns `ghci` with TidalCycles boot file as a subprocess
- Communicates via stdin (send code) and stdout (read responses)
- Manages connection lifecycle: start, send, hush, stop
- Detects errors from GHCi output and surfaces them in the pattern monitor
### Key Methods

```python
class TidalBridge:
    async def start() -> bool           # boot GHCi + Tidal, return success
    async def send(code: str) -> str    # send Tidal code, return GHCi output
    async def hush() -> None            # silence all patterns
    async def set_bpm(bpm: int) -> None # setcps(bpm/60/4)
    async def stop() -> None            # kill subprocess cleanly
    def is_running() -> bool            # health check
```

### Error Handling

- If GHCi crashes, status bar shows `✗ disconnected` and user can press `r` to reconnect
- Parse errors from Tidal are shown inline in the pattern monitor with red highlighting
- Timeout: if GHCi doesn't respond within 5s, treat as hung and offer restart

## Translator (`translator.py`)

### How It Works

1. User types natural language in the chat input
2. Translator calls Claude API with:
   - System prompt containing TidalCycles syntax reference
   - Current active patterns (so it knows context)
   - Current song metadata (BPM, key, genre)
   - The user's request
3. Claude returns Tidal code4. Code appears in the pattern monitor with a confirmation bar:
   ```
   ┌ Generated code ──────────────────────────────────┐
   │ d1 $ s "bd sn bd sn" # gain 0.9                  │
   │                                                    │
   │ Enter: send  ·  e: edit  ·  x: cancel             │
   └───────────────────────────────────────────────────┘
   ```
5. User confirms (Enter), edits (e), or cancels (x)

### System Prompt Context

The translator's system prompt includes:
- TidalCycles mini-notation reference
- SuperDirt sample names (bd, sn, hh, etc.)
- Common effects (gain, pan, speed, crush, delay, room)
- Pattern combinators (stack, cat, every, sometimes)
- Current active patterns and their code
- Song metadata (BPM, key, genre)

### Context Awareness

The translator maintains a rolling context of the current session:
- What patterns are active on each orbit (d1–d16)
- What the user has asked for previously in this session
- The musical key and BPM

This means follow-up requests like "make the hihat busier" or "add some reverb to the bass" work naturally.
## Patterns Library

### Format (`patterns/drums/four-on-the-floor.yml`)

```yaml
name: four-on-the-floor
category: drums
genre: [house, techno]
bpm_range: [118, 135]
description: "Classic house kick pattern — four even kicks per bar"
code: |
  d1 $ s "bd bd bd bd" # gain 1.1
tags: [kick, steady, foundation]
```

### Browsing

Press `p` in music mode to open the pattern browser:
- Filterable by category (drums/bass/synth), genre, tags
- Preview: selecting a pattern shows its code and description
- Load: Enter sends the pattern to the appropriate orbit
- Patterns are composable — load multiple and they layer

## Visualiser (`visualiser/index.html`)

### Tech

- Pure HTML/JS/Canvas — no build step, no npm
- Web Audio API for frequency analysis (FFT) and waveform data
- Connects to system audio output (requires user permission)
### Display

- Dark background (`#0a0a0a`)
- Frequency bars or waveform visualisation (toggleable)
- BPM, key, and song name overlay in bottom-left
- Fullscreen-friendly — fills the browser window
- Responds to audio reactively (bars pulse with the beat)

### Launch

- `v` key in music mode opens `index.html` in Chrome
- Uses `open -a "Google Chrome" path/to/index.html`
- Visualiser runs independently — closing it doesn't affect audio

## Installation (`setup/install.sh`)

One-shot script that handles the full dependency chain:

```bash
#!/bin/bash
# TidalCycles installer for macOS
# Run: bash brain/music/setup/install.sh

# 1. Homebrew deps
brew install haskell-stack ghc cabal-install

# 2. SuperCollider
brew install --cask supercollider

# 3. TidalCycles (Haskell library)
cabal update
cabal install tidal
# 4. SuperDirt (SuperCollider quark)
# Launches SC and installs SuperDirt + samples
sclang -e 'Quarks.install("SuperDirt"); SuperDirt.start;'

# 5. Verify
ghci -e ':script BootTidal.hs'
```

Script is idempotent — safe to re-run. Checks for existing installations before installing.

## Implementation Scope

### New files

| File | Purpose |
|------|---------|
| `brain/music/__init__.py` | Lazy-load guard |
| `brain/music/tidal_bridge.py` | GHCi subprocess management |
| `brain/music/translator.py` | NL → Tidal code via Claude API |
| `brain/music/song_manager.py` | Song CRUD, ID generation, naming |
| `brain/music/visualiser/index.html` | Audio visualiser |
| `brain/music/setup/install.sh` | Dependency installer |
| `brain/command_centre/music_mode.py` | CC widget: layout, keys, status bar |
### Modified files

| File | Change |
|------|--------|
| `brain/command_centre/app.py` | Add `m` key binding, music mode activation, lazy import |
| `brain/command_centre/status_bar.py` | Music mode status bar format |
| `brain/command_centre/help_data.yml` | Add music mode keys and `/music` command |
| `.gitignore` | Add `brain/music/samples/` |

### Not changed

- `stream_list.py` — untouched
- `tile_grid.py` — untouched
- `diagram_grid.py` — untouched
- `router.py` — `/music` command just activates music mode, no new routing logic
- `brain/core/` — reuses existing `claude_client.py` as-is

## Testing

- Unit tests for `song_manager.py` (ID generation, sequential numbering, name generation)
- Unit tests for `tidal_bridge.py` (mock subprocess, send/receive, error detection)
- Unit tests for `translator.py` (mock Claude API, code extraction, context building)
- Unit tests for `music_mode.py` (key bindings, panel layout, status bar rendering)
- Integration test for full flow: NL input → translator → bridge → GHCi (requires Tidal installed)
- No tests for visualiser (pure HTML, manual testing)

## Open Questions

1. **Audio routing for visualiser** — Web Audio API needs access to system audio. May need BlackHole or similar virtual audio device to pipe SuperCollider output to Chrome.
2. **Pattern orbit assignment** — should the translator auto-assign orbits (d1, d2, etc.) or should the user specify? Leaning towards auto-assign with manual override.
3. **MIDI support** — future consideration. TidalCycles supports MIDI out. Park for now (YAGNI).
4. **Sample management** — how to handle custom samples beyond the default SuperDirt set. The `samples/` folder is gitignored, but we may want a catalogue file.