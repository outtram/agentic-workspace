# Task Registry & Dedup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate duplicate tasks and ID collisions by introducing a central task registry with dedup and scoped git auto-sync.

**Architecture:** A single `task_registry.py` module becomes the only way to create/update tasks. It manages a `task-registry.yml` file as the ID source of truth, performs dedup on every create, and auto-syncs data paths via git.

**Tech Stack:** Python 3, PyYAML, difflib (stdlib), subprocess (git), existing WorkItem model

---

### Task 1: Create task_registry.py — Git Sync Layer

**Files:**
- Create: `.claude/scripts/task_registry.py`
- Reference: `.claude/reminders/core/paths.py`

**Step 1: Write the failing test**

Create test file:

```python
# .claude/scripts/tests/test_task_registry.py
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_git_sync_pulls_before_read(tmp_path):
    """Auto-sync should git pull before reading registry"""
    from task_registry import TaskRegistry

    reg = TaskRegistry(work_dir=tmp_path / "work" / "tasks")
    with patch.object(reg, '_git_run') as mock_git:
        mock_git.return_value = (True, "")
        reg._git_pull()
        mock_git.assert_called_once()
        args = mock_git.call_args[0][0]
        assert "pull" in args


def test_git_sync_pushes_after_write(tmp_path):
    """Auto-sync should git push after writing registry"""
    from task_registry import TaskRegistry

    reg = TaskRegistry(work_dir=tmp_path / "work" / "tasks")
    with patch.object(reg, '_git_run') as mock_git:
        mock_git.return_value = (True, "")
        reg._git_push(["test.yml"])
        assert any("push" in str(call) for call in mock_git.call_args_list)


def test_git_sync_only_syncs_data_paths(tmp_path):
    """Should only sync files under auto-sync paths"""
    from task_registry import TaskRegistry

    reg = TaskRegistry(work_dir=tmp_path / "work" / "tasks")
    assert reg._should_auto_sync(".claude/work/tasks/OUT-123.md") is True
    assert reg._should_auto_sync(".claude/memory/projects/active.yml") is True
    assert reg._should_auto_sync("brain/knowledge.yml") is True
    assert reg._should_auto_sync(".claude/scripts/import-reminders.py") is False
    assert reg._should_auto_sync(".claude/agents/work-tracker.md") is False
    assert reg._should_auto_sync("docs/plans/design.md") is False


def test_git_sync_handles_offline_gracefully(tmp_path):
    """Should log warning and continue when offline"""
    from task_registry import TaskRegistry

    reg = TaskRegistry(work_dir=tmp_path / "work" / "tasks")
    with patch.object(reg, '_git_run') as mock_git:
        mock_git.return_value = (False, "fatal: unable to access remote")
        # Should not raise
        reg._git_pull()
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest .claude/scripts/tests/test_task_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'task_registry'`

**Step 3: Write the git sync layer**

```python
# .claude/scripts/task_registry.py
"""
Task Registry — single source of truth for task IDs and dedup.

All task creation MUST go through this module.
"""

import os
import re
import subprocess
import yaml
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reminders.core.paths import PROJECT_ROOT, TASK_DIR, WORK_DIR
from reminders.core.models import WorkItem
from reminders.adapters.workitems import WorkItemFileAdapter

REGISTRY_PATH = WORK_DIR / "task-registry.yml"

AUTO_SYNC_PATHS = [
    ".claude/work/",
    ".claude/memory/",
    "brain/",
]

FUZZY_MATCH_THRESHOLD = 0.85


class TaskRegistry:
    """Central registry for task IDs, dedup, and auto-sync."""

    def __init__(self, work_dir: Path = None):
        self.work_dir = Path(work_dir) if work_dir else TASK_DIR
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.work_dir.parent / "task-registry.yml"
        self.project_root = PROJECT_ROOT
        self.workitems = WorkItemFileAdapter(work_dir=self.work_dir)

    # --- Git Sync ---

    def _should_auto_sync(self, file_path: str) -> bool:
        """Check if file is within auto-sync paths."""
        return any(file_path.startswith(p) for p in AUTO_SYNC_PATHS)

    def _git_run(self, args: list[str]) -> tuple[bool, str]:
        """Run a git command from project root. Returns (success, output)."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return False, str(e)

    def _git_pull(self):
        """Pull latest from remote. Logs warning on failure."""
        ok, output = self._git_run(["pull", "--rebase"])
        if not ok:
            print(f"Warning: git pull failed (offline?): {output.strip()[:100]}")

    def _git_push(self, changed_files: list[str]):
        """Stage, commit, and push auto-sync files."""
        # Filter to auto-sync paths only
        sync_files = [f for f in changed_files if self._should_auto_sync(f)]
        if not sync_files:
            return

        # Stage
        self._git_run(["add"] + sync_files)

        # Commit
        ok, _ = self._git_run(["commit", "-m", f"registry: auto-sync {len(sync_files)} file(s)"])
        if not ok:
            return  # Nothing to commit

        # Push
        ok, output = self._git_run(["push"])
        if not ok:
            print(f"Warning: git push failed (offline?): {output.strip()[:100]}")

    def _update_last_synced(self):
        """Update last_synced timestamp in registry."""
        data = self._read_registry()
        data["last_synced"] = datetime.now().isoformat()
        self._write_registry(data)

    # --- Registry I/O ---

    def _read_registry(self) -> dict:
        """Read the registry file. Creates default if missing."""
        if not self.registry_path.exists():
            return self._create_default_registry()

        with open(self.registry_path, 'r') as f:
            data = yaml.safe_load(f)

        return data or self._create_default_registry()

    def _write_registry(self, data: dict):
        """Write registry to disk."""
        with open(self.registry_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def _create_default_registry(self) -> dict:
        """Create empty registry with defaults."""
        return {
            "schema_version": 1,
            "next_id": 220,
            "last_synced": datetime.now().isoformat(),
            "entries": {}
        }

    # --- Dedup ---

    def find_duplicate(
        self,
        title: str,
        reminder_id: Optional[str] = None
    ) -> Optional[str]:
        """Check for duplicate. Returns existing OUT-ID or None."""
        data = self._read_registry()
        entries = data.get("entries", {})

        for out_id, entry in entries.items():
            # Exact match on reminder_id
            if reminder_id and entry.get("reminder_id") == reminder_id:
                return out_id

            # Fuzzy title match
            ratio = SequenceMatcher(
                None,
                title.lower().strip(),
                entry.get("title", "").lower().strip()
            ).ratio()
            if ratio >= FUZZY_MATCH_THRESHOLD:
                return out_id

        return None

    # --- Task CRUD ---

    def create_task(
        self,
        title: str,
        source: str = "manual",
        reminder_id: Optional[str] = None,
        description: str = "",
        priority: str = "low",
        due_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        list_name: str = "Reminders",
        eisenhower_quadrant: Optional[str] = None,
        eisenhower_urgent: bool = False,
        eisenhower_important: bool = False,
    ) -> Optional[str]:
        """Create a new task. Returns OUT-ID or None if duplicate."""
        # Sync before read
        self._git_pull()

        # Check dedup
        existing = self.find_duplicate(title, reminder_id)
        if existing:
            print(f"Skipping duplicate: '{title}' matches {existing}")
            return None

        # Read registry and assign ID
        data = self._read_registry()
        next_id = data.get("next_id", 220)
        out_id = f"OUT-{next_id}"
        data["next_id"] = next_id + 1

        # Auto-classify if not provided
        if not eisenhower_quadrant:
            eisenhower_quadrant = self._classify_quadrant(
                priority, due_date, bool(description),
                eisenhower_urgent, eisenhower_important
            )
            eisenhower_urgent, eisenhower_important = self._get_urgent_important(
                eisenhower_quadrant
            )

        # Create WorkItem and write file
        now = datetime.now()
        work_item = WorkItem(
            id=out_id,
            title=title,
            status="todo",
            priority=priority,
            due_date=due_date,
            tags=tags or [],
            eisenhower_quadrant=eisenhower_quadrant,
            eisenhower_urgent=eisenhower_urgent,
            eisenhower_important=eisenhower_important,
            source=source,
            reminder_id=reminder_id,
            reminder_list=list_name if reminder_id else None,
            description=description,
            created=now,
            updated=now
        )
        file_path = self.workitems.create(work_item)

        # Update registry
        data["entries"][out_id] = {
            "title": title,
            "file": file_path.name,
            "source": source,
            "reminder_id": reminder_id,
            "status": "todo",
            "created": now.strftime("%Y-%m-%d"),
        }
        data["last_synced"] = now.isoformat()
        self._write_registry(data)

        # Sync after write
        rel_registry = str(self.registry_path.relative_to(self.project_root))
        rel_task = str(file_path.relative_to(self.project_root))
        self._git_push([rel_registry, rel_task])

        return out_id

    def update_status(self, out_id: str, status: str):
        """Update task status in both file and registry."""
        self._git_pull()

        # Update registry
        data = self._read_registry()
        if out_id in data.get("entries", {}):
            data["entries"][out_id]["status"] = status
            data["last_synced"] = datetime.now().isoformat()
            self._write_registry(data)

        # Update file
        work_item = self.workitems.read(out_id)
        if work_item:
            work_item.status = status
            work_item.updated = datetime.now()
            self.workitems.update(work_item)

            # Sync
            rel_registry = str(self.registry_path.relative_to(self.project_root))
            file_path = self.workitems._find_file(out_id)
            if file_path:
                rel_task = str(file_path.relative_to(self.project_root))
                self._git_push([rel_registry, rel_task])

    def list_tasks(self, status: Optional[str] = None) -> dict:
        """List tasks from registry, optionally filtered by status."""
        data = self._read_registry()
        entries = data.get("entries", {})
        if status:
            return {k: v for k, v in entries.items() if v.get("status") == status}
        return entries

    # --- Helpers ---

    def _classify_quadrant(self, priority, due_date, has_body, urgent, important):
        """Auto-classify Eisenhower quadrant."""
        if urgent and important:
            return "q1"
        elif not urgent and important:
            return "q2"
        elif urgent and not important:
            return "q3"
        return "q4"

    def _get_urgent_important(self, quadrant):
        """Derive urgent/important from quadrant."""
        return (
            quadrant in ("q1", "q3"),  # urgent
            quadrant in ("q1", "q2"),  # important
        )
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest .claude/scripts/tests/test_task_registry.py -v`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add .claude/scripts/task_registry.py .claude/scripts/tests/test_task_registry.py
git commit -m "OUT-registry: Add task registry with git sync layer"
```

---

### Task 2: Create task_registry.py — Dedup Tests

**Files:**
- Modify: `.claude/scripts/tests/test_task_registry.py`

**Step 1: Add dedup tests**

Append to test file:

```python
def test_find_duplicate_by_reminder_id(tmp_path):
    """Should find duplicate by exact reminder_id match"""
    from task_registry import TaskRegistry

    work_dir = tmp_path / "work" / "tasks"
    work_dir.mkdir(parents=True)

    reg = TaskRegistry(work_dir=work_dir)

    # Seed registry with an entry
    data = reg._create_default_registry()
    data["entries"]["OUT-220"] = {
        "title": "Buy tickets",
        "file": "OUT-220-buy-tickets.md",
        "source": "reminder",
        "reminder_id": "x-apple-reminder://ABC123",
        "status": "todo",
        "created": "2026-02-25",
    }
    reg._write_registry(data)

    # Should find by reminder_id
    result = reg.find_duplicate("Completely different title", reminder_id="x-apple-reminder://ABC123")
    assert result == "OUT-220"

    # Should not find unrelated
    result = reg.find_duplicate("Completely different title", reminder_id="x-apple-reminder://XYZ789")
    assert result is None


def test_find_duplicate_by_fuzzy_title(tmp_path):
    """Should find duplicate by fuzzy title match (>85%)"""
    from task_registry import TaskRegistry

    work_dir = tmp_path / "work" / "tasks"
    work_dir.mkdir(parents=True)

    reg = TaskRegistry(work_dir=work_dir)

    data = reg._create_default_registry()
    data["entries"]["OUT-220"] = {
        "title": "Paint brackets",
        "file": "OUT-220-paint-brackets.md",
        "source": "reminder",
        "status": "todo",
        "created": "2026-02-25",
    }
    reg._write_registry(data)

    # Very similar title — should match
    result = reg.find_duplicate("Paint the brackets")
    assert result == "OUT-220"

    # Completely different — should not match
    result = reg.find_duplicate("Buy groceries")
    assert result is None


def test_create_task_prevents_duplicates(tmp_path):
    """create_task should return None for duplicates"""
    from task_registry import TaskRegistry

    work_dir = tmp_path / "work" / "tasks"
    work_dir.mkdir(parents=True)

    reg = TaskRegistry(work_dir=work_dir)

    # Mock git so it doesn't actually run
    with patch.object(reg, '_git_pull'), patch.object(reg, '_git_push'):
        # First create should succeed
        result1 = reg.create_task(title="Fix van handles", source="reminder")
        assert result1 is not None
        assert result1.startswith("OUT-")

        # Second create with same title should be blocked
        result2 = reg.create_task(title="Fix van handles", source="email_import")
        assert result2 is None


def test_create_task_increments_id(tmp_path):
    """Each create should get a unique incrementing ID"""
    from task_registry import TaskRegistry

    work_dir = tmp_path / "work" / "tasks"
    work_dir.mkdir(parents=True)

    reg = TaskRegistry(work_dir=work_dir)

    with patch.object(reg, '_git_pull'), patch.object(reg, '_git_push'):
        id1 = reg.create_task(title="Task one", source="manual")
        id2 = reg.create_task(title="Task two", source="manual")
        id3 = reg.create_task(title="Task three", source="manual")

        num1 = int(id1.split("-")[1])
        num2 = int(id2.split("-")[1])
        num3 = int(id3.split("-")[1])

        assert num2 == num1 + 1
        assert num3 == num2 + 1
```

**Step 2: Run tests**

Run: `python3 -m pytest .claude/scripts/tests/test_task_registry.py -v`
Expected: PASS (all 8 tests)

**Step 3: Commit**

```bash
git add .claude/scripts/tests/test_task_registry.py
git commit -m "OUT-registry: Add dedup and ID increment tests"
```

---

### Task 3: Generate Initial Registry from Existing Files

**Files:**
- Create: `.claude/scripts/generate-registry.py`
- Creates: `.claude/work/task-registry.yml`

**Step 1: Write the migration script**

```python
#!/usr/bin/env python3
"""Generate task-registry.yml from existing task files (one-time migration)"""

import sys
import yaml
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reminders.core.paths import TASK_DIR, WORK_DIR

REGISTRY_PATH = WORK_DIR / "task-registry.yml"


def extract_frontmatter(file_path):
    """Extract YAML frontmatter from markdown file"""
    content = file_path.read_text()
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None
    return yaml.safe_load(match.group(1))


def main():
    print("Generating task-registry.yml from existing files...")

    entries = {}
    highest_id = 219

    for file_path in sorted(TASK_DIR.glob("OUT-*.md")):
        if file_path.name == "template.md":
            continue

        fm = extract_frontmatter(file_path)
        if not fm:
            print(f"  Skipping {file_path.name} — no frontmatter")
            continue

        out_id = fm.get("id", "")
        if not out_id:
            continue

        # Track highest ID
        try:
            num = int(out_id.split("-")[1])
            highest_id = max(highest_id, num)
        except (ValueError, IndexError):
            pass

        entries[out_id] = {
            "title": fm.get("title", ""),
            "file": file_path.name,
            "source": fm.get("source", "manual"),
            "reminder_id": fm.get("reminder_id"),
            "status": fm.get("status", "todo"),
            "created": fm.get("created", datetime.now().strftime("%Y-%m-%d")),
        }
        print(f"  Added {out_id}: {fm.get('title', '')[:50]}")

    registry = {
        "schema_version": 1,
        "next_id": highest_id + 1,
        "last_synced": datetime.now().isoformat(),
        "entries": entries,
    }

    with open(REGISTRY_PATH, 'w') as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print()
    print(f"Registry written to {REGISTRY_PATH}")
    print(f"  Entries: {len(entries)}")
    print(f"  Next ID: {highest_id + 1}")


if __name__ == "__main__":
    main()
```

**Step 2: Run the migration**

Run: `python3 .claude/scripts/generate-registry.py`
Expected: Output showing ~41 entries added, next_id set correctly

**Step 3: Verify registry**

Run: `python3 -c "import yaml; data=yaml.safe_load(open('.claude/work/task-registry.yml')); print(f'Entries: {len(data[\"entries\"])}, Next ID: {data[\"next_id\"]}')""`
Expected: `Entries: 41, Next ID: 307` (or similar)

**Step 4: Commit**

```bash
git add .claude/scripts/generate-registry.py .claude/work/task-registry.yml
git commit -m "OUT-registry: Generate initial task registry from existing files"
```

---

### Task 4: Update Reminders Importer to Use Registry

**Files:**
- Modify: `.claude/scripts/import-reminders.py:141-168,250-291`

**Step 1: Replace ID generation and dedup with registry calls**

Replace the `check_duplicate()`, `get_next_task_id()` functions and the main loop to use `TaskRegistry`. Key changes:

- Remove `check_duplicate()` (lines 141-151) — registry handles this
- Remove `get_next_task_id()` (lines 154-168) — registry handles this
- Replace main loop (lines 268-291) to call `registry.create_task()` instead of manual file writes

The `create_task_file()` function (lines 171-247) still generates the content, but the ID comes from the registry and the dedup check happens first.

**Step 2: Run import to verify**

Run: `python3 .claude/scripts/import-reminders.py`
Expected: All existing reminders show "Skipping duplicate", no new files created

**Step 3: Commit**

```bash
git add .claude/scripts/import-reminders.py
git commit -m "OUT-registry: Update reminders importer to use task registry"
```

---

### Task 5: Update Reminders Manager to Use Registry

**Files:**
- Modify: `.claude/reminders/core/manager.py:24,36-37,106-107,215-231`

**Step 1: Replace in-memory ID counter with registry**

Key changes:
- Remove `self._next_id` (line 24) and `_get_next_work_item_id()` (lines 215-231)
- In `create_reminder()` (line 36-37): replace `f"OUT-{self._next_id}"` with `self.registry.create_task()`
- In `import_reminder()` (line 106-107): same replacement
- Add `self.registry = TaskRegistry(work_dir=work_dir)` to `__init__`

**Step 2: Run existing tests**

Run: `python3 -m pytest .claude/reminders/ -v` (if tests exist)
Otherwise manually test: create a reminder via manager, verify it appears in registry

**Step 3: Commit**

```bash
git add .claude/reminders/core/manager.py
git commit -m "OUT-registry: Update reminders manager to use task registry"
```

---

### Task 6: Update Dashboard Generator to Use Registry

**Files:**
- Modify: `.claude/scripts/generate-dashboard.py:49-94`

**Step 1: Add registry-first lookup with file fallback**

In `scan_work_items()`, try reading from registry first. If registry exists, use it for quick listing. Fall back to scanning files if registry is missing.

**Step 2: Generate dashboard and verify counts**

Run: `python3 .claude/scripts/generate-dashboard.py`
Expected: Total count matches registry entry count (no duplicates)

**Step 3: Commit**

```bash
git add .claude/scripts/generate-dashboard.py
git commit -m "OUT-registry: Update dashboard to read from registry"
```

---

### Task 7: Update Work-Tracker Agent Docs

**Files:**
- Modify: `.claude/agents/work-tracker.md`

**Step 1: Add registry instructions**

Add a section explaining that all task creation must go through `task_registry.py`. Remove references to manual ID assignment. Document the `TaskRegistry` API.

**Step 2: Commit**

```bash
git add .claude/agents/work-tracker.md
git commit -m "OUT-registry: Update work-tracker agent to reference registry"
```

---

### Task 8: End-to-End Verification

**Step 1: Run full import cycle**

```bash
python3 .claude/scripts/import-reminders.py
```

Expected: All existing reminders skipped as duplicates

**Step 2: Generate dashboard**

```bash
python3 .claude/scripts/generate-dashboard.py
```

Expected: Count matches actual unique tasks (~41)

**Step 3: Test creating a new task via registry**

```python
from task_registry import TaskRegistry
reg = TaskRegistry()
result = reg.create_task(title="Test task from registry", source="manual")
print(result)  # Should print OUT-307 or similar
```

**Step 4: Verify git sync worked**

```bash
git log --oneline -5
```

Expected: See auto-sync commit for the new task

**Step 5: Clean up test task**

Delete the test task file and remove from registry.

**Step 6: Final commit**

```bash
git add -A .claude/work/
git commit -m "OUT-registry: Verified end-to-end — task registry complete"
```
