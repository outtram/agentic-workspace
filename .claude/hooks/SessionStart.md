# SessionStart Hook

> Optional: Auto-import reminders and show Q1 priorities when starting a new session

## When This Runs
Every time you start a new Claude Code session in this project.

## What It Does
Displays a quick summary of your Q1 priorities without running a full import (unless you want it to).

## Prompt

**Session Started for agentic-workspace**

Check if Troy wants a daily review:

```bash
# Quick check: How many reminders imported today?
grep "2026-02-12: Imported from Reminders" .claude/work/tasks/OUT-2*.md 2>/dev/null | wc -l
```

If 0 or it's been > 4 hours since last import, ask:

"👋 Morning Troy! Would you like to:
1. **Do daily review** - Import reminders + generate dashboard
2. **Just show Q1** - View existing priorities
3. **Skip** - Continue with session"

Otherwise, just show:
"📊 **Today's Q1 Priorities** (X tasks)
- [Task 1]
- [Task 2]
- [Task 3]

Type `/daily-review` to refresh or 'show all Q1' to see full list."

## Configuration
To enable/disable this hook:
- **Enable:** This file exists
- **Disable:** Delete or rename this file

## Notes
- Non-intrusive: Just a quick prompt, not automatic import
- Smart: Only suggests refresh if data is stale
- Fast: Uses cached data when available
- Optional: Easy to skip if you're jumping into a task
