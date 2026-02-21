---
id: OUT-272
title: "OutBot: Remember This handler"
type: task
status: done
priority: high
created: '2026-02-17T17:00:00'
updated: '2026-02-17T17:00:00'
branch: feature/OUT-272-outbot-remember-this
source: outbot-backlog
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
tags: [outbot, memory, clawbot]
---

# OutBot: "Remember This" Handler

## Why
ClawBot feels like it knows you because users can say "remember I hate morning meetings" and it writes to memory files. OutBot currently has static memory files that never change. This is the #1 missing feature for making OutBot feel like it's learning.

## What
Detect when Troy says "remember X" (or similar) during chat and write to the appropriate memory file:
- User preferences/facts → append to USER.md
- OutBot behaviour changes → append to SOUL.md
- General facts/notes → append to a new NOTES.md or MEMORY.md

## Acceptance Criteria
- [ ] Detect "remember", "don't forget", "note that", "keep in mind" triggers
- [ ] Use Claude to classify what type of memory it is (user pref, personality tweak, fact)
- [ ] Append to the correct .claude/memory/*.md file
- [ ] Confirm to Troy what was remembered
- [ ] Handle "forget X" / "stop remembering X" to remove entries
- [ ] Works in both CLI and voice modes
- [ ] Tests covering detect → classify → write → confirm flow

## Implementation Notes
- NanoClaw pattern: agent writes directly to CLAUDE.md files
- Keep it simple — append to a `## Learned` section at bottom of each file
- Use ClaudeClient.judge() (haiku) for fast classification
- File writes should be atomic (write to temp, rename)

## References
- `docs/openclaw-research/01-memory-system.md` — NanoClaw memory architecture
- `brain/chat.py` — OutBotCLI.send() is where detection should hook in
- `.claude/memory/USER.md` — target file for user preferences
