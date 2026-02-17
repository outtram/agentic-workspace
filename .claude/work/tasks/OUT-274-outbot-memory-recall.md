---
id: OUT-274
title: "OutBot: Memory recall from past conversations"
type: task
status: done
priority: medium
created: '2026-02-17T17:00:00'
updated: '2026-02-17T17:00:00'
branch: feature/OUT-274-outbot-memory-recall
source: outbot-backlog
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
tags: [outbot, memory, clawbot]
depends_on: OUT-273
---

# OutBot: Memory Recall from Past Conversations

## Why
Once conversations are archived (OUT-273), OutBot should be able to search them when relevant. If Troy says "what did we talk about last week?" or "remember that SSL issue?", OutBot should grep its conversation archives and include relevant context.

## What
Add memory recall capability — OutBot searches its archived conversations and memory files when the current message suggests it needs historical context.

## Acceptance Criteria
- [ ] Detect when a message references past conversations ("last time", "remember when", "what did we discuss")
- [ ] Search `.claude/memory/conversations/*.md` using keyword grep
- [ ] Search `.claude/memory/*.md` for relevant stored memories
- [ ] Include top 2-3 relevant snippets in the prompt context
- [ ] Don't search on every message — only when past context is likely needed
- [ ] Keep search results under 1000 tokens to avoid bloating the prompt
- [ ] Tests for trigger detection and search result formatting

## Implementation Notes
- Use subprocess grep for simplicity (no vector search needed yet)
- Add a `_search_memory()` method to OutBotCLI
- Use haiku to judge whether a message needs memory recall (fast/cheap)
- Format search results as `<memory_recall>...</memory_recall>` XML in prompt

## References
- `docs/openclaw-research/01-memory-system.md` — "agent can grep conversation archives"
- `docs/openclaw-research/06-human-feel-secrets.md` — Conversational Continuity
