# Claude Code vs OutBot: Capability Map

> Reference document for deciding where to build new features.
> Last updated: 25 Feb 2026

## The Key Insight

```
Claude Code = BUILD things (code, docs, dashboards, tasks)
OutBot      = REACH you (notifications, email, voice, mobile)
```

They're complementary, not competing:
- **Claude Code** is the workshop — you sit down, open the terminal, and build
- **OutBot** is the assistant that follows you — Telegram in your pocket, voice in the car, email on the go

---

## Capability Matrix

### SHARED (both systems access these)

| Capability | Claude Code | OutBot | Shared Resource |
|---|---|---|---|
| Task management | Full CRUD via agents + CLI | Create + read via TaskRegistry | `.claude/work/tasks/`, `task-registry.yml` |
| Reminders sync | `reminder sync` CLI + reverse sync | `run_daily_review()` calls same sync | `.claude/reminders/` package |
| Eisenhower dashboard | `generate-dashboard.py` | Same script via `run_daily_review()` | `.claude/dashboards/`, gist |
| Memory (read) | All agents read memory | Personality loader reads SOUL/USER/AGENTS | `.claude/memory/` |
| Memory (write) | memory-writer (YAML) + shared_memory.py (USER.md/LEARNED.md) | Remember/forget via chat (USER.md, LEARNED.md) | `.claude/memory/` |
| Git sync | Auto-commit/push on task changes | None (piggybacks on Claude Code's commits) | GitHub repo |

### CLAUDE CODE ONLY

| Capability | Details | Why OutBot Can't |
|---|---|---|
| **Write code** | Edit/create any file, run tests, build features | OutBot is chat-only, no file editing tools |
| **Structured memory** | memory-writer agent updates YAML domains | OutBot writes facts to markdown, not YAML domains |
| **Enrich tasks** | work-item-enricher adds steps, categories, context | OutBot has no enrichment pipeline |
| **Wrangle overdue** | overdue-wrangler proposes reschedule/archive/escalate | OutBot only reports overdue, doesn't act on them |
| **Meta-agent** | Detects missing agents/skills, recommends builds | Self-improvement loop, no OutBot equivalent |
| **Skills (26)** | pptx, xlsx, docx, pdf, TDD, frontend-design, etc. | OutBot has no skill system |
| **Agents (9)** | Overseer orchestrates multi-step pipelines | OutBot has single orchestrator, no agent delegation |
| **Git operations** | Commits, PRs, branch management | OutBot has no git access |
| **Plan mode** | Explore > plan > approve > implement workflow | OutBot is conversational, no structured planning |
| **MCP tools** | Playwright, desktop-commander, Pencil design | OutBot has no MCP integration |

### OUTBOT ONLY

| Capability | Details | Why Claude Code Can't |
|---|---|---|
| **Always-on Telegram** | 24/7 long-polling, responds to messages anytime | Claude Code is session-based, exits when you close terminal |
| **Proactive heartbeat** | Every 60s checks for overdue tasks, sends nudges unprompted | Claude Code only runs when invoked |
| **Email (read + send)** | Gmail IMAP/SMTP — check inbox, compose & send emails | Claude Code has no email integration |
| **Voice mode** | Whisper ASR + macOS TTS, hands-free conversation | Claude Code is text-only |
| **Personality (SOUL.md)** | Consistent persona across conversations, Australian humour | Claude Code follows CLAUDE.md but no persistent persona |
| **Session continuity** | SQLite DB tracks all conversations, 20-message context window | Claude Code compresses context, no persistent DB |
| **Memory recall** | "Remember when we discussed X?" searches past conversations | Claude Code has auto-memory but can't search conversation history |
| **Quiet hours** | No notifications 10pm-7am | Not applicable (manual tool) |
| **Importance judging** | Claude haiku decides if a notification is worth sending | Not applicable (manual tool) |

---

## Where to Build New Things

### Build in Claude Code when:
- It involves **writing code** (features, scripts, agents, skills)
- It involves **file manipulation** (docs, spreadsheets, presentations, PDFs)
- It requires **planning** (multi-step, needs approval, has architectural decisions)
- It needs **testing** (TDD, verification, CI/CD)
- It's a **one-off task** (generate a report, fix a bug, create a dashboard)
- It touches **git** (commits, PRs, branches)

### Build in OutBot when:
- It needs to **reach Troy unprompted** (proactive notifications, scheduled checks)
- It involves **email** (check inbox, send messages, draft responses)
- It needs **24/7 availability** (Telegram bot, always listening)
- It's **conversational** (quick questions, memory recall, "what did we discuss?")
- It requires **voice** (hands-free, driving, cooking)
- It's a **new integration** that should push to Telegram (Calendar, Slack, webhooks)

### Build as SHARED when:
- It's a **data pipeline** that both systems should trigger (like daily review, reminder sync)
- It's a **Python package** in `.claude/reminders/` or `.claude/scripts/` — callable from both
- It's **memory** that both need (SOUL.md, USER.md, work items)

---

## Gaps & Roadmap

### Closed (this session)

| Gap | Fix | Status |
|---|---|---|
| OutBot can't create tasks | Intent detection + TaskRegistry in orchestrator | Done |
| OutBot can't write memory | Wired remember.py into orchestrator message flow | Done |

### Not Worth Closing

| Gap | Reason |
|---|---|
| Claude Code has no email | Use OutBot for email, Claude Code for everything else |

### Future (nice to have)

| Gap | Notes |
|---|---|
| Calendar integration | Build as shared package in `.claude/calendar/`, wire into both heartbeat + daily review |
| OutBot triggering Claude Code agents | e.g. "Hey OutBot, run the enricher on OUT-305" |
| Claude Code sending Telegram messages | e.g. after a long build, notify Troy on Telegram |
| Shared event bus | Both systems publish/subscribe to same events |

---

## Summary

**Q: Can Claude Code do everything OutBot can do?**
No. Claude Code can't send emails, run 24/7, push Telegram notifications, do voice, or recall past conversations.

**Q: Can OutBot do everything Claude Code can do?**
No. OutBot can't write code, edit files, enrich work items, run tests, make git commits, or use any of the 26 skills.

**Q: If I want to build something, where do I go?**
- Building a feature/tool/script → **Claude Code**
- Building a notification/integration/always-on service → **OutBot**
- Building a data pipeline both need → **Shared package** in `.claude/`
