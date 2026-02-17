---
id: OUT-276
title: "OutBot: Terminal-native formatting for CLI mode"
type: task
status: done
priority: medium
created: '2026-02-17T17:00:00'
updated: '2026-02-17T17:00:00'
branch: feature/OUT-276-outbot-terminal-formatting
source: outbot-backlog
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
tags: [outbot, ux, clawbot]
---

# OutBot: Terminal-Native Formatting for CLI Mode

## Why
ClawBot's Secret #3 is "Channel-Native Communication" — format messages for the platform. SOUL.md currently has WhatsApp formatting rules (*bold*, no ## headers) but OutBot now runs in a terminal where those rules don't apply. Terminal mode should use terminal-appropriate formatting.

## What
Adapt the formatter to detect CLI vs WhatsApp mode and apply appropriate formatting:
- **Terminal:** ANSI colours for emphasis, proper indentation, markdown-ish formatting
- **WhatsApp:** Keep existing *bold* and bullet formatting
- **Voice:** Strip ALL formatting (already partly done)

## Acceptance Criteria
- [ ] Detect current channel (cli/whatsapp/voice) in formatter
- [ ] Terminal: use ANSI bold/colour codes for emphasis
- [ ] Terminal: proper line wrapping at terminal width
- [ ] Terminal: keep bullet points and indentation clean
- [ ] Voice: strip to plain text (no formatting at all)
- [ ] WhatsApp: keep existing format_outbound() behaviour
- [ ] Tests for each channel format

## Implementation Notes
- `brain/personality/formatter.py` already has `format_outbound()`
- Add a `channel` parameter: `format_outbound(text, channel="cli")`
- Use `shutil.get_terminal_size()` for line wrapping width

## References
- `docs/openclaw-research/06-human-feel-secrets.md` — Secret #3: Channel-Native Communication
- `brain/personality/formatter.py` — existing formatter
