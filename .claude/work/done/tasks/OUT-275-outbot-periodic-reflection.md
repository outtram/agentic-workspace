---
id: OUT-275
title: "OutBot: Periodic reflection and memory evolution"
type: task
status: done
priority: medium
created: '2026-02-17T17:00:00'
updated: '2026-02-17T17:00:00'
branch: feature/OUT-275-outbot-periodic-reflection
source: outbot-backlog
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
tags: [outbot, memory, clawbot]
depends_on: OUT-272, OUT-273
---

# OutBot: Periodic Reflection and Memory Evolution

## Why
ClawBot doesn't just remember what you explicitly tell it — it notices patterns over time. "Troy always asks about X on Mondays" or "Troy prefers short answers when he's busy." This passive learning is what makes an assistant feel like it truly knows you.

## What
Add a periodic reflection step (via heartbeat or end-of-session) where OutBot reviews recent conversations and updates memory files with observed patterns.

## Acceptance Criteria
- [ ] At end of each session (or daily via heartbeat), review last N messages
- [ ] Use Claude to identify patterns: preferences, habits, topics, communication style
- [ ] Compare against existing USER.md — only add genuinely new observations
- [ ] Append new observations to USER.md under a `## Observed Patterns` section
- [ ] Never overwrite existing manual entries
- [ ] Log what was learned (debug output)
- [ ] Tests for pattern extraction and deduplication

## Implementation Notes
- Run reflection with haiku (cheap, fast) — it's just pattern extraction
- Prompt: "Given these recent conversations, what new facts about Troy should I remember?"
- Compare against existing USER.md content to avoid duplicates
- Rate limit: max 3 new observations per reflection cycle
- Could run as a heartbeat task or as a session-end hook

## Example Output
```markdown
## Observed Patterns
- Prefers voice mode for quick questions, text mode for complex tasks (observed 2026-02-17)
- Often works late (messages after 10pm on weekdays) (observed 2026-02-17)
- Frequently asks about OutBot memory/learning capabilities (observed 2026-02-17)
```

## References
- `brain/heartbeat/scheduler.py` — could run as scheduled task
- `docs/openclaw-research/01-memory-system.md` — memory evolution concepts
- `docs/openclaw-research/06-human-feel-secrets.md` — what makes it feel human
