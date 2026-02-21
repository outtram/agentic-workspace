---
id: OUT-273
title: "OutBot: Conversation archiving"
type: task
status: done
priority: high
created: '2026-02-17T17:00:00'
updated: '2026-02-17T17:00:00'
branch: feature/OUT-273-outbot-conversation-archiving
source: outbot-backlog
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
tags: [outbot, memory, clawbot]
---

# OutBot: Conversation Archiving

## Why
ClawBot archives full conversation transcripts as searchable markdown files before context gets compacted. This means the agent can grep past conversations to recall what was discussed days/weeks ago. OutBot stores messages in SQLite but never creates searchable archives.

## What
When a chat session ends (or periodically), export the conversation to a dated markdown file that OutBot can search later.

## Acceptance Criteria
- [ ] On session end (quit/exit), archive conversation to `.claude/memory/conversations/`
- [ ] File format: `YYYY-MM-DD-summary.md` with messages formatted as readable transcript
- [ ] Include sender names and timestamps
- [ ] Generate a 1-line summary for the filename (use haiku)
- [ ] Archive only if session had > 2 messages (skip empty sessions)
- [ ] Conversation archives are searchable via grep
- [ ] Tests for archive format, filename generation, and minimum message threshold

## Implementation Notes
- NanoClaw pattern: `groups/{name}/conversations/2026-02-15-topic-summary.md`
- Hook into OutBotCLI.run() at the quit point
- Pull messages from SQLite for the current session
- Format as readable markdown (not XML)

## File Format Example
```markdown
# Chat: Debugging SSL certs for voice module
**Date:** 2026-02-17 14:30 - 15:45

**Troy:** voice recording for outbot not working so good help
**OutBot:** Let me check the voice module...
**Troy:** yeah swap out whatever you reckon
...
```

## References
- `docs/openclaw-research/01-memory-system.md` — conversation archiving section
- `docs/openclaw-research/06-human-feel-secrets.md` — Secret #1: Conversational Continuity
- `brain/core/db.py` — Database.get_messages_since() for retrieving messages
