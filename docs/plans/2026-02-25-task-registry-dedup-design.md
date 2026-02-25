# Task Registry & Dedup Design

> Eliminate duplicate tasks and ID collisions across all import sources

## Problem

Three independent systems create task files with no coordination:
1. **Reminders Importer** (`import-reminders.py`) — scans filesystem for next ID
2. **Reminders Manager** (`manager.py`) — uses in-memory counter
3. **Email Import** (Claude Code agent) — ad-hoc ID assignment

This causes:
- **ID collisions** — two different tasks get the same OUT-XXX number
- **Content duplicates** — same reminder imported by different systems
- **Inflated dashboards** — 63 items shown when only ~40 exist

## Solution: Task Registry File

A single `task-registry.yml` file that is the source of truth for all task IDs.

### Registry Schema

```yaml
# .claude/work/task-registry.yml
schema_version: 1
next_id: 307
last_synced: 2026-02-25T14:30:00

entries:
  OUT-223:
    title: "Fire place fix"
    file: "OUT-223-fire-place-fix.md"
    source: reminder
    reminder_id: "x-apple-reminder://ABC123..."
    status: todo
    created: 2026-02-12
```

### Rules

- `next_id` is the only place new IDs come from — incremented atomically on each create
- `entries` is a flat dict keyed by OUT-ID
- Each entry stores just enough for dedup: title, reminder_id, source
- The `.md` file remains the full task — the registry is an index, not a replacement

## Shared Library: task_registry.py

A single Python module that all systems must use. No system creates task files directly.

### API

```python
from task_registry import TaskRegistry

reg = TaskRegistry()

# Create a new task (handles dedup + ID assignment)
task_id = reg.create_task(
    title="Buy Baxter Dury tickets",
    source="reminder",
    reminder_id="x-apple-reminder://...",
    description="...",
    priority="medium",
    due_date="2026-02-27",
    eisenhower_quadrant="q1"
)
# Returns "OUT-307" or None if duplicate detected

# Check for duplicates before creating
dup = reg.find_duplicate(
    title="Buy Baxter Dury tickets",
    reminder_id="x-apple-reminder://..."
)
# Returns existing OUT-ID or None

# Update status
reg.update_status("OUT-307", "done")

# List all tasks
tasks = reg.list_tasks(status="todo")
```

### Dedup Logic

On every `create_task()` call:

1. **Exact match on reminder_id** — if any existing entry has the same reminder_id, skip (return existing ID)
2. **Fuzzy title match** — if any existing entry has >85% similarity (difflib.SequenceMatcher), flag as potential duplicate and skip
3. **ID collision check** — guaranteed impossible since next_id is the only source

### File Write Flow

```
create_task() called
  → git pull (auto-sync paths only)
  → read task-registry.yml
  → check dedup (reminder_id exact, title fuzzy)
  → if duplicate: return existing ID, done
  → assign next_id, increment
  → write OUT-XXX-slug.md file
  → update task-registry.yml
  → git add + commit + push (auto-sync paths only)
  → return new ID
```

## Scoped Git Auto-Sync

Every registry read/write triggers git sync, but only for data paths.

### Auto-sync paths (pull/push on every read/write):

- `.claude/work/` — tasks, bugs, PRDs, registry
- `.claude/memory/` — learned skills, projects, decisions
- `brain/` — OutBot knowledge

### Manual sync only (normal git workflow):

- `.claude/scripts/` — importer code
- `.claude/agents/` — agent definitions
- `.claude/reminders/` — importer library
- `.claude/skills/` — skill definitions
- `.agents/` — skill files
- `docs/` — architecture, plans
- Everything else

### Sync Implementation

```python
def auto_sync(changed_files: list[str]):
    AUTO_SYNC_PATHS = [".claude/work/", ".claude/memory/", "brain/"]

    # Only sync if changed files are within auto-sync paths
    if not any(f.startswith(p) for f in changed_files for p in AUTO_SYNC_PATHS):
        return

    # Pull latest
    git pull --rebase

    # Stage only auto-sync files
    git add <changed_files>
    git commit -m "OUT-XXX: <title>"
    git push

    # On push failure: pull --rebase, re-read registry, retry
```

### Offline Handling

- If git pull/push fails due to no network, log warning and continue
- Set `last_synced` timestamp so staleness is visible
- On next successful sync, any conflicts are resolved (registry merge = keep both entries, renumber if collision)

## Migration Plan

### Step 1: Generate registry from existing files

Scan all `.claude/work/tasks/OUT-*.md` files and build the initial `task-registry.yml` from their frontmatter.

### Step 2: Create task_registry.py shared library

Single Python module with the API above. Place at `.claude/scripts/task_registry.py`.

### Step 3: Update Reminders Importer

Replace `get_next_task_id()` and direct file writes with `TaskRegistry.create_task()`.

### Step 4: Update Reminders Manager

Replace `_next_id` counter and `WorkItemFileAdapter.create()` with `TaskRegistry.create_task()`.

### Step 5: Update work-tracker agent

Add instruction to use `task_registry.py` for all task creation. No more manual ID assignment.

### Step 6: Update dashboard generator

Read from registry for quick task listing. Fall back to scanning files if registry is missing.

## Success Criteria

- Zero duplicate tasks after import
- Zero ID collisions
- All three import systems use the same code path
- Registry stays in sync across laptops via auto git sync
- Dashboard count matches actual unique tasks
