"""Tests for TaskRegistry — git sync, dedup, and CRUD operations."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest
import yaml

# Ensure the scripts directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from task_registry import TaskRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def registry(tmp_path):
    """Create a TaskRegistry pointed at a temp directory with git mocked out."""
    work_dir = tmp_path / ".claude" / "work"
    task_dir = work_dir / "tasks"
    task_dir.mkdir(parents=True)
    registry_file = work_dir / "task-registry.yml"

    reg = TaskRegistry(
        work_dir=work_dir,
        task_dir=task_dir,
        registry_file=registry_file,
        project_root=tmp_path,
    )
    return reg


@pytest.fixture
def seeded_registry(registry):
    """Registry with two pre-existing entries and files."""
    # Seed the registry YAML directly
    data = {
        "schema_version": 1,
        "next_id": 102,
        "last_synced": datetime.now().isoformat(),
        "entries": {
            "OUT-100": {
                "title": "Buy milk",
                "file": "OUT-100-buy-milk.md",
                "source": "reminders",
                "reminder_id": "apple-rem-abc",
                "status": "todo",
                "created": datetime.now().isoformat(),
            },
            "OUT-101": {
                "title": "Fix the login bug",
                "file": "OUT-101-fix-the-login-bug.md",
                "source": "manual",
                "reminder_id": None,
                "status": "todo",
                "created": datetime.now().isoformat(),
            },
        },
    }
    registry.registry_file.write_text(yaml.dump(data, default_flow_style=False))
    registry._load()
    return registry


# ---------------------------------------------------------------------------
# _should_auto_sync tests
# ---------------------------------------------------------------------------

class TestShouldAutoSync:
    def test_work_dir_returns_true(self, registry):
        p = registry.project_root / ".claude" / "work" / "tasks" / "OUT-100.md"
        assert registry._should_auto_sync(p) is True

    def test_memory_dir_returns_true(self, registry):
        p = registry.project_root / ".claude" / "memory" / "projects" / "active.yml"
        assert registry._should_auto_sync(p) is True

    def test_brain_dir_returns_true(self, registry):
        p = registry.project_root / "brain" / "config.yml"
        assert registry._should_auto_sync(p) is True

    def test_random_path_returns_false(self, registry):
        p = registry.project_root / "src" / "index.ts"
        assert registry._should_auto_sync(p) is False

    def test_outside_project_returns_false(self, registry):
        p = Path("/tmp/something/else.md")
        assert registry._should_auto_sync(p) is False


# ---------------------------------------------------------------------------
# Git layer tests
# ---------------------------------------------------------------------------

class TestGitPull:
    @patch("task_registry.subprocess.run")
    def test_calls_git_pull(self, mock_run, registry):
        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.")
        registry._git_pull()
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert "pull" in args[0][0]

    @patch("task_registry.subprocess.run")
    def test_handles_failure_gracefully(self, mock_run, registry):
        mock_run.side_effect = Exception("Network unreachable")
        # Should NOT raise
        registry._git_pull()


class TestGitPush:
    @patch("task_registry.subprocess.run")
    def test_calls_git_push(self, mock_run, registry):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        changed = [registry.project_root / ".claude" / "work" / "tasks" / "OUT-100.md"]
        registry._git_push(changed)
        # Should have called add, commit, push — at least 3 subprocess calls
        assert mock_run.call_count >= 3

    @patch("task_registry.subprocess.run")
    def test_handles_failure_gracefully(self, mock_run, registry):
        mock_run.side_effect = Exception("Push failed")
        changed = [registry.project_root / ".claude" / "work" / "tasks" / "OUT-100.md"]
        # Should NOT raise
        registry._git_push(changed)

    @patch("task_registry.subprocess.run")
    def test_skips_non_syncable_paths(self, mock_run, registry):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        changed = [registry.project_root / "src" / "index.ts"]
        registry._git_push(changed)
        # Should not call git at all since file is outside auto-sync paths
        assert mock_run.call_count == 0


# ---------------------------------------------------------------------------
# Dedup tests
# ---------------------------------------------------------------------------

class TestFindDuplicate:
    def test_finds_by_reminder_id(self, seeded_registry):
        result = seeded_registry.find_duplicate("Anything at all", reminder_id="apple-rem-abc")
        assert result == "OUT-100"

    def test_finds_by_fuzzy_title(self, seeded_registry):
        # "buy milks" is very close to "Buy milk"
        result = seeded_registry.find_duplicate("buy milks")
        assert result == "OUT-100"

    def test_no_match_returns_none(self, seeded_registry):
        result = seeded_registry.find_duplicate("Completely unrelated task")
        assert result is None

    def test_exact_title_match(self, seeded_registry):
        result = seeded_registry.find_duplicate("Buy milk")
        assert result == "OUT-100"


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------

class TestCreateTask:
    @patch.object(TaskRegistry, "_git_push")
    @patch.object(TaskRegistry, "_git_pull")
    def test_returns_none_for_duplicate(self, mock_pull, mock_push, seeded_registry):
        result = seeded_registry.create_task(
            title="Buy milk",
            source="manual",
        )
        assert result is None

    @patch.object(TaskRegistry, "_git_push")
    @patch.object(TaskRegistry, "_git_pull")
    def test_increments_ids(self, mock_pull, mock_push, seeded_registry):
        first_id = seeded_registry.create_task(
            title="Brand new task alpha",
            source="manual",
        )
        assert first_id == "OUT-102"

        second_id = seeded_registry.create_task(
            title="Brand new task beta",
            source="manual",
        )
        assert second_id == "OUT-103"

    @patch.object(TaskRegistry, "_git_push")
    @patch.object(TaskRegistry, "_git_pull")
    def test_creates_file_on_disk(self, mock_pull, mock_push, seeded_registry):
        out_id = seeded_registry.create_task(
            title="Deploy new service",
            source="manual",
            description="Ship the thing",
            priority="high",
        )
        assert out_id is not None
        # File should exist
        files = list(seeded_registry.task_dir.glob(f"{out_id}-*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "Deploy new service" in content
        assert "Ship the thing" in content

    @patch.object(TaskRegistry, "_git_push")
    @patch.object(TaskRegistry, "_git_pull")
    def test_updates_registry_file(self, mock_pull, mock_push, seeded_registry):
        out_id = seeded_registry.create_task(
            title="Registry persistence check",
            source="agent",
        )
        # Re-read from disk
        raw = yaml.safe_load(seeded_registry.registry_file.read_text())
        assert out_id in raw["entries"]
        assert raw["entries"][out_id]["title"] == "Registry persistence check"

    @patch.object(TaskRegistry, "_git_push")
    @patch.object(TaskRegistry, "_git_pull")
    def test_calls_git_pull_and_push(self, mock_pull, mock_push, seeded_registry):
        seeded_registry.create_task(title="Git lifecycle test", source="manual")
        mock_pull.assert_called_once()
        mock_push.assert_called_once()

    @patch.object(TaskRegistry, "_git_push")
    @patch.object(TaskRegistry, "_git_pull")
    def test_create_with_all_fields(self, mock_pull, mock_push, seeded_registry):
        out_id = seeded_registry.create_task(
            title="Full field task",
            source="reminders",
            reminder_id="rem-xyz-999",
            description="Detailed description here",
            priority="high",
            due_date="2026-03-01",
            tags=["urgent", "work"],
            list_name="Work",
            eisenhower_quadrant="q1",
            eisenhower_urgent=True,
            eisenhower_important=True,
        )
        assert out_id is not None
        entry = seeded_registry._data["entries"][out_id]
        assert entry["reminder_id"] == "rem-xyz-999"
        assert entry["source"] == "reminders"


class TestUpdateStatus:
    @patch.object(TaskRegistry, "_git_push")
    @patch.object(TaskRegistry, "_git_pull")
    def test_updates_registry_entry(self, mock_pull, mock_push, seeded_registry):
        # First create the file on disk so update can find it
        seeded_registry.create_task(
            title="Status update test",
            source="manual",
        )
        out_id = "OUT-102"  # next_id was 102

        seeded_registry.update_status(out_id, "done")
        assert seeded_registry._data["entries"][out_id]["status"] == "done"


class TestListTasks:
    def test_list_all(self, seeded_registry):
        entries = seeded_registry.list_tasks()
        assert len(entries) == 2

    def test_filter_by_status(self, seeded_registry):
        entries = seeded_registry.list_tasks(status="todo")
        assert len(entries) == 2

        entries = seeded_registry.list_tasks(status="done")
        assert len(entries) == 0
