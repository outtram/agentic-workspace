"""Tests for saving bump state changes back to task YAML frontmatter."""
import tempfile
from pathlib import Path

import yaml

from brain.command_centre.bump_persist import save_stream_state


def _write_task_file(tmp: Path, tid: str, extra_meta: dict = None) -> Path:
    """Write a minimal task markdown file."""
    meta = {"id": tid, "title": f"Task {tid}", "status": "open"}
    if extra_meta:
        meta.update(extra_meta)
    content = f"---\n{yaml.dump(meta, sort_keys=False)}---\n\n## Description\n\nSome text.\n"
    path = tmp / f"{tid}-test.md"
    path.write_text(content)
    return path


class TestSaveStreamState:
    def test_writes_stream_state_to_frontmatter(self, tmp_path):
        path = _write_task_file(tmp_path, "OUT-100")
        save_stream_state(path, stream_state="back", last_touched="2026-03-11T10:00:00")
        text = path.read_text()
        parts = text.split("---", 2)
        meta = yaml.safe_load(parts[1])
        assert meta["stream_state"] == "back"
        assert meta["last_touched"] == "2026-03-11T10:00:00"

    def test_preserves_existing_fields(self, tmp_path):
        path = _write_task_file(tmp_path, "OUT-100", {"priority": "high"})
        save_stream_state(path, stream_state="new", last_touched="2026-03-11T10:00:00")
        text = path.read_text()
        parts = text.split("---", 2)
        meta = yaml.safe_load(parts[1])
        assert meta["priority"] == "high"
        assert meta["title"] == "Task OUT-100"

    def test_preserves_body(self, tmp_path):
        path = _write_task_file(tmp_path, "OUT-100")
        save_stream_state(path, stream_state="seen", last_touched="2026-03-11T10:00:00")
        text = path.read_text()
        assert "## Description" in text
        assert "Some text." in text

    def test_writes_snoozed_until(self, tmp_path):
        path = _write_task_file(tmp_path, "OUT-100")
        save_stream_state(
            path,
            stream_state="snoozed",
            last_touched="2026-03-11T10:00:00",
            snoozed_until="2026-03-12T09:00:00",
        )
        text = path.read_text()
        parts = text.split("---", 2)
        meta = yaml.safe_load(parts[1])
        assert meta["snoozed_until"] == "2026-03-12T09:00:00"
