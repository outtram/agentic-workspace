"""Tests for stream field defaults and sorting in task_loader."""
from datetime import datetime
from unittest.mock import patch, MagicMock
from pathlib import Path

from brain.command_centre.task_loader import load_tasks


def _mock_task_file(content: str, name: str = "OUT-999-test.md") -> MagicMock:
    """Create a mock Path that returns given content."""
    p = MagicMock(spec=Path)
    p.name = name
    p.read_text.return_value = content
    return p


class TestStreamFieldDefaults:
    """Tasks without stream fields get sensible defaults."""

    @patch("brain.command_centre.task_loader._TASK_DIR")
    def test_missing_stream_state_defaults_to_new(self, mock_dir):
        content = "---\nid: OUT-999\ntitle: Test\nstatus: open\n---\n"
        mock_dir.glob.return_value = [_mock_task_file(content)]
        tasks = load_tasks()
        assert len(tasks) == 1
        assert tasks[0]["stream_state"] == "new"

    @patch("brain.command_centre.task_loader._TASK_DIR")
    def test_missing_last_touched_gets_default(self, mock_dir):
        content = "---\nid: OUT-999\ntitle: Test\nstatus: open\n---\n"
        mock_dir.glob.return_value = [_mock_task_file(content)]
        tasks = load_tasks()
        assert "last_touched" in tasks[0]
        datetime.fromisoformat(tasks[0]["last_touched"])

    @patch("brain.command_centre.task_loader._TASK_DIR")
    def test_missing_source_defaults_to_task(self, mock_dir):
        content = "---\nid: OUT-999\ntitle: Test\nstatus: open\n---\n"
        mock_dir.glob.return_value = [_mock_task_file(content)]
        tasks = load_tasks()
        assert tasks[0]["source"] == "task"

    @patch("brain.command_centre.task_loader._TASK_DIR")
    def test_existing_stream_state_preserved(self, mock_dir):
        content = "---\nid: OUT-999\ntitle: Test\nstatus: open\nstream_state: back\nlast_touched: '2026-03-10T10:00:00'\nsource: email\n---\n"
        mock_dir.glob.return_value = [_mock_task_file(content)]
        tasks = load_tasks()
        assert tasks[0]["stream_state"] == "back"
        assert tasks[0]["source"] == "email"
