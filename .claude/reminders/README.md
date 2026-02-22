# Reminders Manager

Bi-directional sync between macOS Reminders.app and file-native task system.

## Features

- **CLI interface** - Add, list, complete, delete reminders from command line
- **macOS Integration** - Syncs with Reminders.app via AppleScript
- **File-native storage** - Work items stored as markdown files with YAML frontmatter
- **Eisenhower Matrix** - Automatic classification into Q1-Q4 quadrants
- **Event-driven architecture** - Pub/sub event bus for extensibility
- **Multi-dimensional tagging** - Project, context, client, priority tags

## Installation

```bash
cd .claude/reminders
pip install -e ".[dev]"
```

## Usage

### Add a reminder
```bash
# Basic reminder
reminder add "Call Leon"

# With due date and priority
reminder add "Call Leon" --due 2026-02-20 --priority high

# With tags
reminder add "Call Leon" --tag phone --tag urgent

# With description
reminder add "Call Leon" --notes "Discuss equity partner timeline"

# With reminder list
reminder add "Call Leon" --list "Work"
```

### List reminders
```bash
# List all reminders
reminder list

# Compact format
reminder list --format compact

# JSON output
reminder list --format json

# Filter by tag
reminder list --tag urgent

# Filter by Eisenhower quadrant
reminder list --quadrant q1
```

### Complete a reminder
```bash
reminder complete OUT-264
```

### Delete a reminder
```bash
reminder delete OUT-264
```

### Show reminder details
```bash
reminder show OUT-264
```

### Sync from Reminders.app
```bash
# Import all active reminders
reminder sync

# Dry run (see what would be imported)
reminder sync --dry-run

# Import with AI enrichment suggestions for vague tasks
reminder sync --enrich
```

### AI Enrichment - Make Vague Tasks Actionable

The enrichment system detects vague tasks and helps make them clearer:

```bash
# Get interactive help to clarify a vague task
reminder enrich OUT-243

# Example output:
# 🤔 Task looks vague: "Meet with hook online"
# Why: Meeting without clear agenda or desired outcome
#
# Let's make it actionable:
#   • What specifically needs to be done with online?
#   • What's the desired outcome or next action?
#   • What context or background is important?
```

The enricher detects:
- Short titles (< 10 characters)
- Placeholder words ("thing", "stuff")
- Missing or boilerplate descriptions
- Meetings without clear agendas
- Generic actions without outcomes

### Progress Tasks - Complete Next Steps

Help complete the next step of a task:

```bash
# Work on a specific task
reminder progress OUT-264

# Pick from Q1 (urgent & important) tasks
reminder progress --q1

# Interactive workflow:
# 1. Shows task details and overdue warnings
# 2. Lists unchecked steps
# 3. Mark steps complete, add notes, or mark entire task done
```

### Proactive Nudges - Stay on Track

Check for overdue and urgent tasks:

```bash
reminder nudge

# Example output:
# ⚠️  URGENT ATTENTION NEEDED
#
# 🔴 OVERDUE (3 tasks):
#   • OUT-221: Golden plains password (overdue by 38 days)
#   • OUT-220: Tesalatities tiles (overdue by 38 days)
#   • OUT-232: ross peachy meeting setup (overdue by 30 days)
#
# 💡 Recommended actions:
#   1. reminders progress --q1  (work on a Q1 task)
#   2. reminders complete <id>  (mark as done)
```

Nudge shows:
- **Overdue** tasks (past due date)
- **Due today** tasks
- **Due soon** tasks (within 3 days)

## Work Item Files

Reminders are stored as markdown files in `.claude/work/tasks/`:

```markdown
---
id: OUT-264
title: Call Leon
status: todo
priority: high
due_date: 2026-02-20
tags: [phone, urgent]
eisenhower_quadrant: q1
eisenhower_urgent: true
eisenhower_important: true
reminder_id: x-apple-reminder://ABC123
---

## Description

Discuss equity partner timeline
```

## Development

### Run tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=reminders --cov-report=term-missing

# Specific test
pytest tests/unit/test_models.py::test_work_item_creation -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v
```

### Test coverage
Current coverage: **84%** (39/39 tests passing)
- Core modules: 90%+ coverage
- Adapters: High coverage (mock-based testing)

## Architecture

- **core/models.py** - WorkItem and Reminder dataclasses
- **core/events.py** - Event types and EventBus pub/sub system
- **core/manager.py** - RemindersManager orchestrates all operations
- **adapters/applescript.py** - macOS Reminders.app integration
- **adapters/workitems.py** - File I/O for markdown work items
- **plugins/cli.py** - Click CLI interface

See `docs/plans/2026-02-13-reminders-tool-design.md` for complete design documentation.
