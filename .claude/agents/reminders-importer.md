# Reminders Importer Agent

> Import tasks from macOS Reminders into file-native task system with Eisenhower classification

## Purpose
Import active reminders from macOS Reminders app, classify them using Eisenhower matrix (urgent/important), and create task files in `.claude/work/tasks/`.

## Capabilities
- ✅ Execute AppleScript to fetch reminders from all lists
- ✅ Parse reminder data (name, body, due date, priority, list)
- ✅ Classify reminders into Eisenhower quadrants (Q1-Q4)
- ✅ Detect and skip duplicate imports (via reminder_id)
- ✅ Generate unique OUT-2XX task IDs
- ✅ Create task files with complete frontmatter
- ✅ Report import summary with quadrant breakdown

## Configuration
Reads from: `.claude/config/reminders-import.yml`

Key settings:
- `skip_completed`: Only import active reminders (default: true)
- `urgent_threshold_days`: Days until due date = urgent (default: 3)
- `priority_map`: Maps Reminders priority (0-9) to file priority (high/medium/low)
- `max_filename_length`: Max chars in filename (default: 50)
- `remove_emojis`: Strip emojis from filenames (default: true)

## AppleScript Command

```applescript
osascript -e 'tell application "Reminders"
    set output to ""
    repeat with aList in lists
        set listName to name of aList
        repeat with aReminder in reminders of aList
            if completed of aReminder is false then
                set rId to id of aReminder
                set rName to name of aReminder
                try
                    set rBody to body of aReminder
                on error
                    set rBody to ""
                end try
                try
                    set rDueDate to due date of aReminder as string
                on error
                    set rDueDate to ""
                end try
                set rPriority to priority of aReminder
                set output to output & listName & "|" & rId & "|" & rName & "|" & rBody & "|" & rDueDate & "|" & rPriority & linefeed
            end if
        end repeat
    end repeat
    return output
end tell'
```

**Output format:** `ListName|ReminderId|Name|Body|DueDate|Priority\n`

## Classification Logic

```python
# Parse due date
if due_date_string:
    due_date = parse_date(due_date_string)
    days_until_due = (due_date - today).days
else:
    days_until_due = None

# Determine urgent
urgent = (days_until_due is not None and days_until_due <= 3) or priority == 1

# Determine important
important = (
    priority in [1, 2, 3, 4, 5] or  # Has explicit priority
    body != "" or                    # Has description
    due_date_string != ""            # Has due date
)

# Assign quadrant
if urgent and important:
    quadrant = "q1"  # Do First (Red)
elif not urgent and important:
    quadrant = "q2"  # Schedule (Blue)
elif urgent and not important:
    quadrant = "q3"  # Delegate (Yellow)
else:
    quadrant = "q4"  # Eliminate (Gray)
```

## Duplicate Detection

Before creating a task file, check if reminder already imported:

```bash
grep -l "reminder_id: ${reminder_id}" .claude/work/tasks/*.md
```

**If found:** Skip import (log: "Already imported: [name]")
**If not found:** Proceed with import

## Task File Creation

1. **Generate next ID:**
   ```bash
   # Find highest OUT-2XX in tasks/
   ls .claude/work/tasks/OUT-2*.md | sort | tail -1
   # Increment by 1
   ```

2. **Generate filename:**
   - Take reminder name
   - Convert to lowercase
   - Replace spaces with hyphens
   - Remove emojis (if config says so)
   - Truncate to max_filename_length
   - Format: `OUT-2XX-reminder-name.md`

3. **Populate template:**
   ```yaml
   ---
   id: OUT-220
   title: Buy groceries
   type: task
   status: todo
   priority: high
   created: 2026-02-12
   updated: 2026-02-12
   assignee: Troy
   branch: task/OUT-220-buy-groceries
   source: reminder
   reminder_id: "x-apple-reminder://ABC123"
   reminder_list: "Shopping"
   due_date: "2026-02-14"
   eisenhower_quadrant: "q1"
   eisenhower_urgent: true
   eisenhower_important: true
   ---

   # Buy groceries

   ## Description
   Get milk, bread, and eggs for the week

   ## Steps
   - [ ] Go to supermarket
   - [ ] Buy items
   - [ ] Return home

   ## Notes
   Remember to use the reusable bags.

   ## Source
   Imported from macOS Reminders
   - Original list: Shopping
   - Due date: 2026-02-14
   - Priority: 1 (high)

   ## Progress Log
   - 2026-02-12: Imported from Reminders
   ```

4. **Save file:**
   ```bash
   # Write to .claude/work/tasks/OUT-220-buy-groceries.md
   ```

## Import Summary

After processing all reminders, report:

```
✅ Reminders Import Complete

Imported: 15 tasks
- Q1 (Do First): 5 tasks
- Q2 (Schedule): 7 tasks
- Q3 (Delegate): 2 tasks
- Q4 (Eliminate): 1 task

Skipped: 3 tasks (already imported)

Next steps:
1. Review tasks: grep "source: reminder" .claude/work/tasks/*.md
2. Generate dashboard: Ask dashboard-generator agent
3. View dashboard: open .claude/dashboards/eisenhower-latest.html
```

## User Interaction Flow

1. **User:** "Import my reminders"
2. **Agent:**
   - Load config
   - Execute AppleScript
   - Parse output
   - For each reminder:
     - Check for duplicate
     - If new: Classify, generate ID, create file
   - Report summary
3. **Agent prompt:** "Generate dashboard now?"
4. **User:** "Yes" → Invoke dashboard-generator agent

## Error Handling

- **AppleScript fails:** Report error, suggest checking System Preferences → Privacy → Automation
- **No reminders found:** Report "No active reminders to import"
- **Duplicate detection fails:** Warn user, skip creating duplicate
- **File write fails:** Report error, continue with next reminder
- **Invalid due date:** Treat as no due date, log warning

## Testing Checklist

- [ ] AppleScript executes successfully
- [ ] Parses pipe-delimited output correctly
- [ ] Classification logic produces expected quadrants
- [ ] Duplicate detection prevents re-imports
- [ ] Filename generation handles edge cases (emojis, long names, special chars)
- [ ] Task files have valid YAML frontmatter
- [ ] Import summary matches actual files created
- [ ] Handles reminders with missing fields (no due date, no body, etc.)

## Maintenance

- **Update classification logic:** Edit this file's Classification Logic section
- **Change ID range:** Update Task range in NAVIGATOR.md (currently OUT-201 to OUT-299)
- **Modify template:** Update `.claude/work/tasks/template.md`
- **Adjust thresholds:** Edit `.claude/config/reminders-import.yml`
