# Dashboard Generator Agent

> Generate visual Eisenhower Matrix dashboard from file-native task system

## Purpose
Scan `.claude/work/tasks/` and `.claude/work/bugs/`, extract Eisenhower classifications, and generate a static HTML dashboard with 2x2 quadrant layout.

## Capabilities
- ✅ Scan all active work items (tasks + bugs not in done/)
- ✅ Parse YAML frontmatter to extract metadata
- ✅ Group items by Eisenhower quadrant (Q1-Q4)
- ✅ Count tasks per quadrant
- ✅ Load HTML template and inject data as JSON
- ✅ Generate timestamped HTML file
- ✅ Create symlink to latest dashboard
- ✅ Auto-open dashboard in browser

## File Scanning

**Pattern:**
```bash
find .claude/work -name "OUT-*.md" -not -path "*/done/*"
```

**Targets:**
- `.claude/work/tasks/OUT-2XX-*.md`
- `.claude/work/bugs/OUT-1XX-*.md`

**Skip:**
- Files in `done/` subdirectories
- Files without `eisenhower_quadrant` field

## Frontmatter Parsing

Extract these fields from each file:
- `id`: Work item ID (OUT-XXX)
- `title`: Task/bug title
- `status`: Current status (todo/doing/open/etc.)
- `priority`: Priority level (high/medium/low)
- `due_date`: Due date (YYYY-MM-DD or empty)
- `eisenhower_quadrant`: Quadrant (q1/q2/q3/q4 or empty)
- `eisenhower_urgent`: Boolean (for transparency)
- `eisenhower_important`: Boolean (for transparency)
- `source`: Origin (manual/reminder)
- `reminder_list`: Original Reminders list (if applicable)

**Parsing method:**
```bash
# Extract YAML frontmatter between first two --- lines
sed -n '/^---$/,/^---$/p' file.md | grep "^field:" | cut -d: -f2- | xargs
```

## Data Structure

Group tasks into JSON object:

```json
{
  "metadata": {
    "generated_at": "2026-02-12T10:30:00",
    "total_tasks": 15,
    "q1_count": 5,
    "q2_count": 7,
    "q3_count": 2,
    "q4_count": 1
  },
  "q1": [
    {
      "id": "OUT-220",
      "title": "Fix critical auth bug",
      "status": "todo",
      "priority": "high",
      "due_date": "2026-02-14",
      "source": "reminder",
      "reminder_list": "Work",
      "file_path": ".claude/work/tasks/OUT-220-fix-auth-bug.md",
      "description": "Users can't log in after password reset"
    }
  ],
  "q2": [...],
  "q3": [...],
  "q4": [...]
}
```

## HTML Generation

1. **Load template:**
   ```bash
   cat .claude/templates/eisenhower-template.html
   ```

2. **Replace placeholders:**
   - `{timestamp}`: Current datetime (e.g., "2026-02-12 10:30 AM")
   - `{date}`: Current date (e.g., "Feb 12, 2026")
   - `{q1_count}`, `{q2_count}`, `{q3_count}`, `{q4_count}`: Task counts
   - `{INJECTED_JSON_DATA}`: Full JSON data structure

3. **Save file:**
   ```bash
   # Generate timestamp: YYYY-MM-DD-HHMM
   timestamp=$(date +%Y-%m-%d-%H%M)
   output_file=".claude/dashboards/eisenhower-${timestamp}.html"
   # Write HTML content
   echo "${html_content}" > "${output_file}"
   ```

4. **Create symlink:**
   ```bash
   cd .claude/dashboards
   rm -f eisenhower-latest.html
   ln -s "eisenhower-${timestamp}.html" eisenhower-latest.html
   ```

5. **Auto-open in browser:**
   ```bash
   open "file:///Users/touttram/CODE/AAGLOBAL/.claude/dashboards/eisenhower-latest.html"
   ```

## Classification Fallback

If a task has no `eisenhower_quadrant` field:

1. **Check priority and due_date:**
   ```python
   # Urgent if due within 3 days
   urgent = (due_date and days_until_due <= 3) or priority == "high"

   # Important if has priority or due date
   important = (priority in ["high", "medium"]) or due_date

   # Classify
   if urgent and important: quadrant = "q1"
   elif not urgent and important: quadrant = "q2"
   elif urgent and not important: quadrant = "q3"
   else: quadrant = "q4"
   ```

2. **Log warning:**
   ```
   ⚠️ Task OUT-220 missing eisenhower_quadrant, auto-classified as Q1
   ```

3. **Add to dashboard with indicator:**
   - Show "(auto)" badge next to task title

## Dashboard Features

User can interact with:
- **Filter buttons:** "Show All", "Reminders Only", "Manual Tasks Only"
- **Task cards:** Click to expand/collapse details
- **Color coding:** Red (Q1), Blue (Q2), Yellow (Q3), Gray (Q4)
- **Sorting:** Within each quadrant, sort by due date (earliest first)
- **Badges:** Priority, source, due date indicators
- **Dark mode toggle:** Switch between light/dark themes

## Generation Summary

After creating dashboard, report:

```
📊 Dashboard Generated

File: .claude/dashboards/eisenhower-2026-02-12-1030.html
Latest: .claude/dashboards/eisenhower-latest.html

Tasks by Quadrant:
- 🔥 Q1 (Do First): 5 tasks
- 📅 Q2 (Schedule): 7 tasks
- 🔀 Q3 (Delegate): 2 tasks
- 🗑️ Q4 (Eliminate): 1 task

Opening in browser...

Next steps:
1. Review Q1 tasks (urgent & important)
2. Select a task to work on
3. Update status: Ask work-tracker agent
4. Start work: Invoke /using-superpowers
```

## User Interaction Flow

1. **User:** "Generate dashboard"
2. **Agent:**
   - Scan work items
   - Parse frontmatter
   - Group by quadrant
   - Load template
   - Inject data
   - Save HTML file
   - Create symlink
   - Auto-open
   - Report summary
3. **User:** [Views dashboard in browser]
4. **User:** "I'll work on OUT-220"
5. **Agent:** [Invokes work-tracker to update status]

## Error Handling

- **No work items found:** Report "No tasks to display"
- **Template missing:** Report error, suggest checking `.claude/templates/`
- **Invalid YAML:** Skip file, log warning
- **Browser won't open:** Provide file path for manual open
- **Symlink fails:** Continue anyway, report warning

## Regeneration

Dashboard is a **snapshot** at point in time. To update:

1. **After completing tasks:**
   ```bash
   # Move task to done/
   mv .claude/work/tasks/OUT-220-*.md .claude/work/done/tasks/
   # Regenerate dashboard
   ask dashboard-generator agent
   ```

2. **After importing reminders:**
   ```bash
   # Import new reminders
   ask reminders-importer agent
   # Generate updated dashboard
   ask dashboard-generator agent
   ```

3. **Scheduled regeneration (future):**
   - PostToolUse hook triggers regeneration when tasks change
   - Cron job regenerates daily at 8am

## Testing Checklist

- [ ] Scans all tasks and bugs (not in done/)
- [ ] Parses YAML frontmatter correctly
- [ ] Groups tasks by quadrant accurately
- [ ] Handles missing eisenhower_quadrant gracefully
- [ ] Injects JSON data into template correctly
- [ ] Creates timestamped HTML file
- [ ] Symlink points to latest file
- [ ] Browser opens automatically
- [ ] Dashboard renders correctly (all quadrants visible)
- [ ] Filter buttons work (Reminders Only, Show All)
- [ ] Task cards expand/collapse on click
- [ ] Handles 0 tasks in a quadrant (shows empty state)

## Maintenance

- **Update template:** Edit `.claude/templates/eisenhower-template.html`
- **Change quadrant logic:** Update Classification Fallback section
- **Add new filters:** Modify template JavaScript
- **Adjust styling:** Edit template CSS
- **Archive old dashboards:** `rm .claude/dashboards/eisenhower-2026-01-*.html`
