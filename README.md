# AAGLOBAL — Agentic Workspace

> Troy Outtram's AI-powered personal operating system.
> Two interfaces, one shared brain.

## Quick Start

### Claude Code (task management, agent pipelines)

```bash
cd ~/CODE/AAGLOBAL
claude
```

Then say: **"do my daily review"** — the Overseer agent runs the full pipeline.

### OutBot (conversational AI, memory, email)

```bash
cd ~/CODE/AAGLOBAL
python brain/chat.py          # CLI chat
python brain/chat.py --voice  # Voice mode
python brain/main.py          # Telegram bot (mobile + heartbeat)
```

### Cursor IDE (coding and editing)

Open this folder in Cursor. It reads `CLAUDE.md` for project context.

---

## What's in Here

| Folder | What it does |
|---|---|
| `.claude/agents/` | 9 agent definitions (overseer, enricher, wrangler, etc.) |
| `.claude/work/` | File-based work tracking (tasks, bugs, PRDs) |
| `.claude/memory/` | Shared memory (USER.md, SOUL.md, NAVIGATOR.md, YAML domains) |
| `.claude/skills/` | 18 skills (pptx, daily-review, TDD, design, etc.) |
| `.claude/dashboards/` | Generated Eisenhower Matrix HTML dashboards |
| `.claude/reminders/` | macOS Reminders.app sync (Python package) |
| `brain/` | OutBot — conversational AI (chat, voice, Telegram, email, memory) |
| `docs/` | Documentation (architecture, setup, research) |

## Key Documents

| Document | Purpose | Audience |
|---|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Full system architecture with diagrams | Everyone |
| [`CLAUDE.md`](CLAUDE.md) | Project context for Claude Code and Cursor | AI agents |
| [`.claude/memory/NAVIGATOR.md`](.claude/memory/NAVIGATOR.md) | Grep-optimised index for finding anything | AI agents |
| [`docs/FRESH-LAPTOP-SETUP.md`](docs/FRESH-LAPTOP-SETUP.md) | New machine setup guide | Troy |
| [`.claude/reminders/README.md`](.claude/reminders/README.md) | Reminders sync system docs | AI agents |

## Common Commands (Claude Code)

| Say this | What happens |
|---|---|
| "do my daily review" | Full pipeline: import → enrich → wrangle → dashboard |
| "import my reminders" | Pull from macOS Reminders.app into work items |
| "enrich all bare tasks" | Add real steps and categories to stub tasks |
| "wrangle overdue" | Review and action overdue/stale items |
| "what should I work on?" | Show Q1 priorities |
| "audit my agents" | Meta Agent reviews system health |
| "generate dashboard" | Rebuild Eisenhower Matrix HTML |

## Docs Freshness

Architecture and documentation should be reviewed when structural changes are made. The Meta Agent checks for stale docs during weekly reviews. The `> Last updated:` line at the top of `docs/ARCHITECTURE.md` tracks currency.

---

*Built on file-native memory research by Damon McMillan (2026). Zero external dependencies for the core system. Powered by Claude Max plan.*
