---
name: daily-review
description: Import reminders, generate Eisenhower dashboard, and show Q1 priorities. Use when Troy says "/daily-review", "daily review", "morning review", "what are my priorities", or asks for task overview.
---

# Daily Review Skill

> Import reminders, generate Eisenhower dashboard, and show Q1 priorities

## Invocation
```
/daily-review
```

## What This Does

1. **Import from macOS Reminders** - Pull active reminders from all lists
2. **Generate Eisenhower Matrix** - Classify into Q1-Q4 quadrants
3. **Update mobile dashboard** - Push to permanent gist URL
4. **Show Q1 priorities** - Display urgent & important tasks
5. **Open dashboard** - Launch in browser for review

## Prompt

You are performing Troy's daily task review. Execute these steps in order:

### Step 1: Import Reminders
Run the reminders CLI sync with `--quick` flag (only checks last 24h, avoids timeout):
```bash
cd .claude/reminders && python3 -m reminders.plugins.cli sync --quick
```

The sync command will:
- Fetch recently created/modified reminders from macOS Reminders.app
- Create work items in `.claude/work/tasks/`
- Skip duplicates automatically
- Classify into Eisenhower quadrants
- Report stats (new imported, duplicates skipped, breakdown by quadrant)

**Note:** Use `sync` (without `--quick`) for a full reconciliation if needed.

### Step 2: Generate Dashboard
Run the dashboard generator:
```bash
python3 .claude/scripts/generate-dashboard.py
```

Confirm:
- Dashboard generated successfully
- Mobile gist updated
- File paths for local and mobile viewing

### Step 3: Check for Urgent/Overdue Tasks
Run the nudge command to check for overdue and urgent tasks:
```bash
cd .claude/reminders && python3 -m reminders.plugins.cli nudge
```

This will show:
- Overdue tasks (past due date)
- Due today tasks
- Due soon tasks (within 3 days)

### Step 4: Analyze Q1 Tasks
Read the Q1 tasks from the generated dashboard data and display:
- **Total Q1 tasks** (urgent & important)
- **Top 3 Q1 tasks** with due dates
- **Overdue tasks** highlighted in red

### Step 5: Daily Summary
Provide a concise summary:

```
📊 Daily Review Complete

Imported: X new reminders
Current workload:
- 🔥 Q1 (Do First): X tasks
- 📅 Q2 (Schedule): X tasks
- 🔀 Q3 (Delegate): X tasks
- 🗑️ Q4 (Eliminate): X tasks

🎯 Top 3 Priorities Today:
1. [Task name] - Due: [date]
2. [Task name] - Due: [date]
3. [Task name] - Due: [date]

📱 Mobile: https://gist.githack.com/outtram/20f5befb1e2f8cef427b784e6860ddf8/raw/eisenhower-dashboard.html
💻 Local: open .claude/dashboards/eisenhower-latest.html
```

### Step 6: Optional Actions
Ask Troy if he wants to:
- [ ] Start working on a specific Q1 task (use `reminders progress --q1`)
- [ ] Enrich a vague task (use `reminders enrich <id>`)
- [ ] Move any Q3/Q4 tasks to backlog
- [ ] Archive completed tasks
- [ ] Done for now

## Best Practices

- **Run in the morning** - Start your day with clear priorities
- **Quick check** - Takes ~10 seconds to see your Q1
- **Mobile ready** - Dashboard auto-updates for on-the-go viewing
- **ADHD-friendly** - Visual, colour-coded, minimal cognitive load

## Notes

- Only imports ACTIVE reminders (completed ones are skipped)
- Duplicate detection prevents re-importing same reminders
- Mobile URL stays permanent, content refreshes automatically
- Dashboard opens automatically in browser for review
