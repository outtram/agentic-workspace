"""
Task Registry — single source of truth for task IDs across all systems.

Prevents duplicate IDs and provides git-sync for collaborative work.
"""

import logging
import subprocess
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import yaml

# ---------------------------------------------------------------------------
# Make the reminders package importable from this script location
# This file lives at: <PROJECT_ROOT>/.claude/scripts/task_registry.py
# We need: <PROJECT_ROOT>/.claude/reminders/
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR.parent))

from reminders.core.models import WorkItem
from reminders.adapters.workitems import WorkItemFileAdapter
from reminders.core.paths import (
    WORK_DIR as DEFAULT_WORK_DIR,
    TASK_DIR as DEFAULT_TASK_DIR,
    PROJECT_ROOT as DEFAULT_PROJECT_ROOT,
)

logger = logging.getLogger(__name__)

# Paths that should trigger automatic git sync
AUTO_SYNC_PREFIXES = [".claude/work/", ".claude/memory/", "brain/"]

FUZZY_THRESHOLD = 0.85


class TaskRegistry:
    """Central registry for task IDs with git sync and dedup."""

    def __init__(
        self,
        work_dir: Path = None,
        task_dir: Path = None,
        registry_file: Path = None,
        project_root: Path = None,
    ):
        self.project_root = Path(project_root or DEFAULT_PROJECT_ROOT)
        self.work_dir = Path(work_dir or DEFAULT_WORK_DIR)
        self.task_dir = Path(task_dir or DEFAULT_TASK_DIR)
        self.registry_file = Path(
            registry_file or (self.work_dir / "task-registry.yml")
        )

        self._adapter = WorkItemFileAdapter(work_dir=self.task_dir)
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Registry I/O
    # ------------------------------------------------------------------

    def _default_data(self) -> dict:
        """Return a fresh empty registry."""
        return {
            "schema_version": 1,
            "next_id": 300,
            "last_synced": datetime.now().isoformat(),
            "entries": {},
        }

    def _load(self):
        """Load registry from YAML file, creating default if missing."""
        if self.registry_file.exists():
            raw = self.registry_file.read_text()
            self._data = yaml.safe_load(raw) or self._default_data()
        else:
            self._data = self._default_data()
            self._save()

    def _save(self):
        """Persist registry to YAML file."""
        self._data["last_synced"] = datetime.now().isoformat()
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.registry_file.write_text(
            yaml.dump(self._data, default_flow_style=False, sort_keys=False)
        )

    # ------------------------------------------------------------------
    # Git sync layer
    # ------------------------------------------------------------------

    def _should_auto_sync(self, path: Path) -> bool:
        """Return True if the path is inside an auto-sync directory."""
        try:
            rel = path.resolve().relative_to(self.project_root.resolve())
        except ValueError:
            return False

        rel_str = str(rel)
        return any(
            rel_str == prefix.rstrip("/") or rel_str.startswith(prefix)
            for prefix in AUTO_SYNC_PREFIXES
        )

    def _git_pull(self):
        """Run git pull --rebase before reads. Fails silently if offline."""
        try:
            result = subprocess.run(
                ["git", "pull", "--rebase"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                self._load()
            else:
                logger.warning("git pull returned %d: %s", result.returncode, result.stderr[:100])
        except Exception as exc:
            logger.warning("git pull failed (offline?): %s", exc)

    def _git_push(self, changed_files: list[Path]):
        """Stage, commit, and push only files inside auto-sync paths."""
        syncable = [f for f in changed_files if self._should_auto_sync(f)]
        if not syncable:
            return

        try:
            # Stage each file using its path relative to project root
            for f in syncable:
                rel = f.resolve().relative_to(self.project_root.resolve())
                subprocess.run(
                    ["git", "add", str(rel)],
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

            subprocess.run(
                ["git", "commit", "-m", "auto: task-registry sync"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=15,
            )

            subprocess.run(
                ["git", "push"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception as exc:
            logger.warning("git push failed (offline?): %s", exc)

    # ------------------------------------------------------------------
    # Dedup
    # ------------------------------------------------------------------

    def find_duplicate(
        self, title: str, reminder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Return existing OUT-ID if a duplicate is found, else None.

        Checks:
        1. Exact match on reminder_id (if provided)
        2. Fuzzy title match (>85% similarity via SequenceMatcher)
        """
        entries = self._data.get("entries", {})

        # 1. Exact reminder_id match
        if reminder_id:
            for out_id, entry in entries.items():
                if entry.get("reminder_id") == reminder_id:
                    return out_id

        # 2. Fuzzy title match
        normalised_title = title.strip().lower()
        for out_id, entry in entries.items():
            existing = entry.get("title", "").strip().lower()
            ratio = SequenceMatcher(None, normalised_title, existing).ratio()
            if ratio >= FUZZY_THRESHOLD:
                return out_id

        return None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_task(
        self,
        title: str,
        source: str = "manual",
        reminder_id: Optional[str] = None,
        description: Optional[str] = None,
        priority: str = "low",
        due_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        list_name: Optional[str] = None,
        eisenhower_quadrant: str = "q4",
        eisenhower_urgent: bool = False,
        eisenhower_important: bool = False,
        parent: Optional[str] = None,
        prd: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a new task. Returns OUT-ID or None if duplicate detected.

        1. Pulls latest from git
        2. Checks for duplicates
        3. Assigns next_id
        4. Writes file via WorkItemFileAdapter
        5. Updates registry
        6. If parent specified, updates parent's children list
        7. Pushes changes
        """
        self._git_pull()

        # Dedup check
        existing = self.find_duplicate(title, reminder_id=reminder_id)
        if existing:
            logger.info("Duplicate detected: %s matches %s", title, existing)
            return None

        # Validate parent exists if specified
        if parent:
            entries = self._data.get("entries", {})
            if parent not in entries:
                logger.warning("create_task: parent %s not found in registry", parent)
                return None

        # Assign ID
        next_num = self._data.get("next_id", 300)
        out_id = f"OUT-{next_num}"
        self._data["next_id"] = next_num + 1

        # Build WorkItem
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
            reminder_list=list_name,
            description=description or "",
            parent=parent,
            prd=prd,
            created=now,
            updated=now,
        )

        # Write file
        file_path = self._adapter.create(work_item)
        changed_files = [file_path, self.registry_file]

        # Update registry entries
        entry = {
            "title": title,
            "file": file_path.name,
            "source": source,
            "reminder_id": reminder_id,
            "status": "todo",
            "created": now.isoformat(),
        }
        if parent:
            entry["parent"] = parent
        if prd:
            entry["prd"] = prd
        self._data.setdefault("entries", {})[out_id] = entry
        self._save()

        # Bidirectional link: update parent's children list
        if parent:
            parent_files = self._link_child_to_parent(parent, out_id)
            changed_files.extend(parent_files)

        # Push changed files
        self._git_push(changed_files)

        return out_id

    def add_child(self, parent_id: str, child_id: str):
        """Link an existing task as a child of a parent (bidirectional)."""
        self._git_pull()

        entries = self._data.get("entries", {})
        if parent_id not in entries:
            logger.warning("add_child: parent %s not found", parent_id)
            return
        if child_id not in entries:
            logger.warning("add_child: child %s not found", child_id)
            return

        changed_files = [self.registry_file]

        # Update registry
        entries[child_id].setdefault("parent", parent_id)
        entries[parent_id].setdefault("children", [])
        if child_id not in entries[parent_id]["children"]:
            entries[parent_id]["children"].append(child_id)
        self._save()

        # Update child file: set parent
        child_item = self._adapter.read(child_id)
        if child_item:
            child_item.parent = parent_id
            child_item.updated = datetime.now()
            self._adapter.update(child_item)
            child_file = self._adapter._find_file(child_id)
            if child_file:
                changed_files.append(child_file)

        # Update parent file: add to children list
        parent_files = self._link_child_to_parent(parent_id, child_id)
        changed_files.extend(parent_files)

        self._git_push(changed_files)

    def _link_child_to_parent(self, parent_id: str, child_id: str) -> list[Path]:
        """Add child_id to parent's children list in file. Returns changed file paths."""
        changed = []
        parent_item = self._adapter.read(parent_id)
        if parent_item:
            if child_id not in parent_item.children:
                parent_item.children.append(child_id)
            parent_item.updated = datetime.now()
            self._adapter.update(parent_item)
            parent_file = self._adapter._find_file(parent_id)
            if parent_file:
                changed.append(parent_file)

            # Also update registry entry
            entries = self._data.get("entries", {})
            if parent_id in entries:
                entries[parent_id].setdefault("children", [])
                if child_id not in entries[parent_id]["children"]:
                    entries[parent_id]["children"].append(child_id)
                self._save()
        return changed

    def update_status(self, out_id: str, status: str):
        """Update the status of a task in both the registry and the file."""
        self._git_pull()

        entries = self._data.get("entries", {})
        if out_id not in entries:
            logger.warning("update_status: %s not found in registry", out_id)
            return

        # Update registry
        entries[out_id]["status"] = status
        self._save()

        # Update file via adapter
        changed_files = [self.registry_file]
        work_item = self._adapter.read(out_id)
        if work_item:
            work_item.status = status
            work_item.updated = datetime.now()
            self._adapter.update(work_item)
            # Resolve the task file path for git push
            task_file = self._adapter._find_file(out_id)
            if task_file:
                changed_files.append(task_file)

        self._git_push(changed_files)

    def active_entries_with_reminder_id(self) -> dict[str, str]:
        """Return {reminder_id: out_id} for non-done entries with a reminder_id."""
        self._git_pull()
        entries = self._data.get("entries", {})
        return {
            entry["reminder_id"]: out_id
            for out_id, entry in entries.items()
            if entry.get("reminder_id") and entry.get("status") not in ("done", "cancelled")
        }

    def list_tasks(self, status: Optional[str] = None) -> dict:
        """
        Return registry entries, optionally filtered by status.

        Returns dict of {OUT-ID: entry_dict}.
        """
        self._git_pull()
        entries = self._data.get("entries", {})
        if status is None:
            return dict(entries)
        return {
            out_id: entry
            for out_id, entry in entries.items()
            if entry.get("status") == status
        }
