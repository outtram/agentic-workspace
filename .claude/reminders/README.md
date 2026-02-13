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
cd /Users/touttram/CODE/AAGLOBAL/.claude/reminders
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
