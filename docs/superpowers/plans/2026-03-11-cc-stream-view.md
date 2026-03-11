# CC Stream View Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an inbox-style Stream View to Command Centre with bump system (t/b/s), view cycling, split chat layout, and proactive polling.

**Architecture:** New `StreamList` widget (same Container pattern as TileGrid/DiagramGrid) with a `bump.py` module for state transitions and undo. Data model extended with `stream_state`, `last_touched`, `source` fields in task frontmatter. Heartbeat bridge gets email/reminder polling. View cycling via `v` key.

**Tech Stack:** Python, Textual (TUI framework), YAML frontmatter, existing task loader pipeline.

**Spec:** `docs/superpowers/specs/2026-03-11-cc-stream-view-design.md`

---

## Chunk 1: Data Model + Bump Logic

### Task 1: Bump module — state transitions and undo

**Files:**
- Create: `brain/command_centre/bump.py`
- Create: `brain/tests/test_command_centre/test_bump.py`

- [ ] **Step 1: Write failing tests for bump state transitions**

```python
# brain/tests/test_command_centre/test_bump.py
"""Tests for bump state machine and undo stack."""
from datetime import datetime, timedelta
from brain.command_centre.bump import (
    bump_top,
    bump_back,
    snooze,
    undo_last,
    mark_seen,
    stream_sort_key,
    check_snoozed,
    STREAM_NEW,
    STREAM_SEEN,
    STREAM_BACK,
)


def _make_task(tid="OUT-1", state="new", last_touched=None, source="task"):
    """Helper to build a task dict."""
    return {
        "id": tid,
        "title": f"Task {tid}",
        "stream_state": state,
        "last_touched": last_touched or datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "snoozed_until": None,
        "status": "open",
    }


class TestBumpTop:
    def test_sets_state_to_new(self):
        task = _make_task(state="seen")
        undo_stack = []
        result = bump_top(task, undo_stack)
        assert result["stream_state"] == STREAM_NEW

    def test_updates_last_touched(self):
        old_time = "2026-01-01T00:00:00"
        task = _make_task(state="seen", last_touched=old_time)
        undo_stack = []
        result = bump_top(task, undo_stack)
        assert result["last_touched"] > old_time

    def test_pushes_undo_entry(self):
        task = _make_task(state="back")
        undo_stack = []
        bump_top(task, undo_stack)
        assert len(undo_stack) == 1
        assert undo_stack[0]["prev_state"] == "back"


class TestBumpBack:
    def test_sets_state_to_back(self):
        task = _make_task(state="new")
        undo_stack = []
        result = bump_back(task, undo_stack)
        assert result["stream_state"] == STREAM_BACK

    def test_pushes_undo_entry(self):
        task = _make_task(state="new")
        undo_stack = []
        bump_back(task, undo_stack)
        assert len(undo_stack) == 1
        assert undo_stack[0]["prev_state"] == "new"


class TestMarkSeen:
    def test_new_becomes_seen(self):
        task = _make_task(state="new")
        result = mark_seen(task)
        assert result["stream_state"] == STREAM_SEEN

    def test_back_stays_back(self):
        task = _make_task(state="back")
        result = mark_seen(task)
        assert result["stream_state"] == STREAM_BACK


class TestSnooze:
    def test_sets_snoozed_until(self):
        task = _make_task(state="new")
        undo_stack = []
        result = snooze(task, hours=1, undo_stack=undo_stack)
        assert result["snoozed_until"] is not None

    def test_check_snoozed_returns_expired(self):
        past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        tasks = [_make_task(tid="OUT-1")]
        tasks[0]["snoozed_until"] = past
        tasks[0]["stream_state"] = "snoozed"
        expired = check_snoozed(tasks)
        assert len(expired) == 1
        assert expired[0]["id"] == "OUT-1"

    def test_check_snoozed_ignores_future(self):
        future = (datetime.now() + timedelta(hours=1)).isoformat(timespec="seconds")
        tasks = [_make_task(tid="OUT-1")]
        tasks[0]["snoozed_until"] = future
        tasks[0]["stream_state"] = "snoozed"
        expired = check_snoozed(tasks)
        assert len(expired) == 0


class TestUndo:
    def test_restores_previous_state(self):
        task = _make_task(state="new")
        undo_stack = []
        bump_back(task, undo_stack)
        assert task["stream_state"] == STREAM_BACK
        restored = undo_last(task, undo_stack)
        assert restored["stream_state"] == "new"

    def test_empty_stack_returns_none(self):
        task = _make_task()
        result = undo_last(task, [])
        assert result is None


class TestStreamSortKey:
    def test_new_before_seen(self):
        new_task = _make_task(state="new")
        seen_task = _make_task(state="seen")
        assert stream_sort_key(new_task) < stream_sort_key(seen_task)

    def test_seen_before_back(self):
        seen_task = _make_task(state="seen")
        back_task = _make_task(state="back")
        assert stream_sort_key(seen_task) < stream_sort_key(back_task)

    def test_newer_before_older_within_group(self):
        newer = _make_task(state="new", last_touched="2026-03-11T10:00:00")
        older = _make_task(state="new", last_touched="2026-03-10T10:00:00")
        assert stream_sort_key(newer) < stream_sort_key(older)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest brain/tests/test_command_centre/test_bump.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'brain.command_centre.bump'`

- [ ] **Step 3: Implement bump.py**

```python
# brain/command_centre/bump.py
"""Bump state machine — top/back/snooze/undo for stream view."""
from datetime import datetime, timedelta

STREAM_NEW = "new"
STREAM_SEEN = "seen"
STREAM_BACK = "back"
STREAM_SNOOZED = "snoozed"

_STATE_ORDER = {STREAM_NEW: 0, STREAM_SEEN: 1, STREAM_BACK: 2, STREAM_SNOOZED: 3}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _push_undo(task: dict, undo_stack: list) -> None:
    """Save current state to undo stack before modifying."""
    undo_stack.append({
        "task_id": task["id"],
        "prev_state": task.get("stream_state", STREAM_NEW),
        "prev_last_touched": task.get("last_touched", ""),
        "prev_snoozed_until": task.get("snoozed_until"),
    })


def bump_top(task: dict, undo_stack: list) -> dict:
    """Mark task as NEW and update last_touched. Returns modified task."""
    _push_undo(task, undo_stack)
    task["stream_state"] = STREAM_NEW
    task["last_touched"] = _now_iso()
    task["snoozed_until"] = None
    return task


def bump_back(task: dict, undo_stack: list) -> dict:
    """Mark task as BACK. Returns modified task."""
    _push_undo(task, undo_stack)
    task["stream_state"] = STREAM_BACK
    task["last_touched"] = _now_iso()
    return task


def mark_seen(task: dict) -> dict:
    """Mark NEW task as SEEN on open. BACK items stay BACK."""
    if task.get("stream_state") == STREAM_NEW:
        task["stream_state"] = STREAM_SEEN
        task["last_touched"] = _now_iso()
    return task


def snooze(task: dict, hours: int, undo_stack: list) -> dict:
    """Snooze task for given hours. Returns modified task."""
    _push_undo(task, undo_stack)
    wake_time = datetime.now() + timedelta(hours=hours)
    task["stream_state"] = STREAM_SNOOZED
    task["snoozed_until"] = wake_time.isoformat(timespec="seconds")
    return task


def check_snoozed(tasks: list[dict]) -> list[dict]:
    """Return tasks whose snooze has expired."""
    now = datetime.now()
    expired = []
    for t in tasks:
        if t.get("stream_state") != STREAM_SNOOZED:
            continue
        until = t.get("snoozed_until")
        if not until:
            continue
        try:
            wake = datetime.fromisoformat(until)
            if wake <= now:
                expired.append(t)
        except (ValueError, TypeError):
            continue
    return expired


def undo_last(task: dict, undo_stack: list) -> dict | None:
    """Restore task to its previous state. Returns None if stack empty."""
    if not undo_stack:
        return None
    entry = undo_stack.pop()
    task["stream_state"] = entry["prev_state"]
    task["last_touched"] = entry["prev_last_touched"]
    task["snoozed_until"] = entry.get("prev_snoozed_until")
    return task


def stream_sort_key(task: dict) -> tuple:
    """Sort key: state group (NEW < SEEN < BACK), then newest first.

    Returns a tuple that sorts correctly with Python's default ascending sort.
    """
    state = task.get("stream_state", STREAM_NEW)
    order = _STATE_ORDER.get(state, 0)
    # Negate timestamp so newer sorts first (smaller key = higher position)
    last_touched = task.get("last_touched", "")
    return (order, "" if not last_touched else _invert_timestamp(last_touched))


def _invert_timestamp(iso: str) -> str:
    """Invert ISO timestamp for descending sort within ascending key.

    We want newer timestamps to sort BEFORE older ones.
    Simple trick: negate by prefixing with inverse character sort.
    """
    # Use inverted string — chr(126 - ord(c)) for each digit
    return "".join(chr(126 - ord(c)) if c.isdigit() else c for c in iso)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest brain/tests/test_command_centre/test_bump.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add brain/command_centre/bump.py brain/tests/test_command_centre/test_bump.py
git commit -m "CC stream: add bump state machine with undo + tests"
```

---

### Task 2: Extend task_loader with stream fields

**Files:**
- Modify: `brain/command_centre/task_loader.py`
- Create: `brain/tests/test_command_centre/test_stream_loader.py`

- [ ] **Step 1: Write failing tests for stream field loading**

```python
# brain/tests/test_command_centre/test_stream_loader.py
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
        # Should be a valid ISO string
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest brain/tests/test_command_centre/test_stream_loader.py -v`
Expected: FAIL — `stream_state` not in task dict

- [ ] **Step 3: Add stream field defaults to task_loader.py**

In `brain/command_centre/task_loader.py`, add after the `t["_weight"] = weight` line (around line 116):

```python
        # Stream view fields — default for tasks without them
        if "stream_state" not in t:
            t["stream_state"] = "new"
        if "last_touched" not in t:
            t["last_touched"] = datetime.now().isoformat(timespec="seconds")
        if "source" not in t:
            t["source"] = "task"
        if "snoozed_until" not in t:
            t["snoozed_until"] = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest brain/tests/test_command_centre/test_stream_loader.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Verify existing tests still pass**

Run: `python3 -m pytest brain/tests/test_command_centre/ -x -q`
Expected: All existing tests PASS (no regressions)

- [ ] **Step 6: Commit**

```bash
git add brain/command_centre/task_loader.py brain/tests/test_command_centre/test_stream_loader.py
git commit -m "CC stream: add stream_state/last_touched/source defaults to task loader"
```

---

### Task 3: Bump persistence — save stream state to task files

**Files:**
- Create: `brain/command_centre/bump_persist.py`
- Create: `brain/tests/test_command_centre/test_bump_persist.py`

- [ ] **Step 1: Write failing tests for bump persistence**

```python
# brain/tests/test_command_centre/test_bump_persist.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest brain/tests/test_command_centre/test_bump_persist.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement bump_persist.py**

```python
# brain/command_centre/bump_persist.py
"""Persist bump state changes to task YAML frontmatter."""
from pathlib import Path

import yaml


def save_stream_state(
    path: Path,
    stream_state: str,
    last_touched: str,
    snoozed_until: str | None = None,
) -> None:
    """Update stream fields in a task file's YAML frontmatter.

    Preserves all existing fields and the markdown body.
    """
    text = path.read_text()
    if not text.startswith("---"):
        return

    parts = text.split("---", 2)
    if len(parts) < 3:
        return

    meta = yaml.safe_load(parts[1])
    if not isinstance(meta, dict):
        return

    meta["stream_state"] = stream_state
    meta["last_touched"] = last_touched
    if snoozed_until is not None:
        meta["snoozed_until"] = snoozed_until
    elif "snoozed_until" in meta:
        del meta["snoozed_until"]

    new_text = f"---\n{yaml.dump(meta, default_flow_style=False, sort_keys=False)}---{parts[2]}"
    path.write_text(new_text)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest brain/tests/test_command_centre/test_bump_persist.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add brain/command_centre/bump_persist.py brain/tests/test_command_centre/test_bump_persist.py
git commit -m "CC stream: add bump persistence to task frontmatter"
```

---

## Chunk 2: StreamList Widget

### Task 4: StreamList widget — rendering and navigation

**Files:**
- Create: `brain/command_centre/stream_list.py`
- Create: `brain/tests/test_command_centre/test_stream_list.py`

- [ ] **Step 1: Write failing tests for stream row rendering**

```python
# brain/tests/test_command_centre/test_stream_list.py
"""Tests for StreamList widget rendering."""
from brain.command_centre.stream_list import render_stream_row


def _make_task(tid="OUT-1", state="new", title="Test Task", source="task", last_touched="2026-03-11T10:00:00"):
    return {
        "id": tid,
        "title": title,
        "stream_state": state,
        "source": source,
        "last_touched": last_touched,
        "snoozed_until": None,
    }


class TestRenderStreamRow:
    def test_new_item_has_green_dot(self):
        row = render_stream_row(_make_task(state="new"), focused=False)
        assert "●" in row
        assert "NEW" in row

    def test_seen_item_has_circle(self):
        row = render_stream_row(_make_task(state="seen"), focused=False)
        assert "○" in row
        assert "NEW" not in row

    def test_back_item_has_open_circle(self):
        row = render_stream_row(_make_task(state="back"), focused=False)
        assert "◌" in row
        assert "BACK" in row

    def test_focused_item_has_cursor(self):
        row = render_stream_row(_make_task(), focused=True)
        assert "▸" in row

    def test_title_in_output(self):
        row = render_stream_row(_make_task(title="My Task"), focused=False)
        assert "My Task" in row

    def test_source_label_in_output(self):
        row = render_stream_row(_make_task(source="email"), focused=False)
        assert "email" in row
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest brain/tests/test_command_centre/test_stream_list.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement stream_list.py**

```python
# brain/command_centre/stream_list.py
"""Stream view widget — inbox-style scrollable list sorted by recency."""
from datetime import datetime

from textual.containers import Container, VerticalScroll
from textual.widgets import Static

from .sanitiser import sanitise

# Source label colours
_SOURCE_COLOURS = {
    "email": "#FF6B35",
    "reminder": "#d4aa00",
    "task": "#00D4AA",
}


def _relative_time(iso_str: str) -> str:
    """Convert ISO timestamp to relative time string like '2m ago'."""
    try:
        dt = datetime.fromisoformat(iso_str)
        delta = datetime.now() - dt
        secs = int(delta.total_seconds())
        if secs < 0:
            return "now"
        if secs < 60:
            return f"{secs}s ago"
        mins = secs // 60
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days < 7:
            return f"{days}d ago"
        weeks = days // 7
        return f"{weeks}w ago"
    except (ValueError, TypeError):
        return ""


def render_stream_row(task: dict, focused: bool = False) -> str:
    """Render a single stream row as Rich markup."""
    state = task.get("stream_state", "new")
    title = sanitise(task.get("title", "Untitled")).replace("[", r"\[")
    if len(title) > 60:
        title = title[:57] + "..."

    source = task.get("source", "task")
    source_colour = _SOURCE_COLOURS.get(source, "#888888")
    last_touched = task.get("last_touched", "")
    rel_time = _relative_time(last_touched)

    if focused:
        icon = "[#FF6B35]▸[/]"
    elif state == "new":
        icon = "[#00D4AA]●[/]"
    elif state == "seen":
        icon = "[#666666]○[/]"
    else:  # back
        icon = "[#444444]◌[/]"

    badge = ""
    if not focused:
        if state == "new":
            badge = "[#00D4AA on #00D4AA20] NEW [/] "
        elif state == "back":
            badge = "[#666666 on #333333] BACK [/] "

    # Title brightness by state
    if state == "new" or focused:
        title_markup = f"[bold]{title}[/]"
    elif state == "seen":
        title_markup = f"[#999999]{title}[/]"
    else:  # back
        title_markup = f"[#666666]{title}[/]"

    source_markup = f"[{source_colour}]{source}[/]"
    time_markup = f"[dim]{rel_time}[/]"

    return f" {icon}  {badge}{title_markup}  {source_markup}  {time_markup}"


class StreamList(Container):
    """Inbox-style scrollable stream of tasks."""

    DEFAULT_CSS = """
    StreamList {
        padding: 0;
        overflow: hidden;
    }
    #stream-notification {
        height: auto;
        max-height: 2;
        display: none;
        padding: 0 2;
        background: #1a2e1a;
    }
    #stream-scroll {
        height: 1fr;
        scrollbar-size: 1 1;
    }
    .stream-row {
        height: 1;
        padding: 0 1;
    }
    .stream-row.focused {
        background: #2a2000;
    }
    .stream-row.state-new {
        /* bright left border via content — CSS can't do per-row borders easily */
    }
    .stream-row.state-back {
        opacity: 0.5;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tasks: list[dict] = []
        self._focus_index: int = 0

    def compose(self):
        yield Static(id="stream-notification")
        with VerticalScroll(id="stream-scroll"):
            # Pre-create enough rows — we'll show/hide as needed
            for i in range(100):
                yield Static(id=f"srow-{i}", classes="stream-row")

    def update_items(
        self,
        tasks: list[dict],
        focus_index: int,
    ):
        """Re-render all stream rows."""
        self._tasks = tasks
        self._focus_index = focus_index

        for i in range(100):
            try:
                row = self.query_one(f"#srow-{i}", Static)
            except Exception:
                break

            row.remove_class("focused", "state-new", "state-seen", "state-back")

            if i < len(tasks):
                task = tasks[i]
                is_focused = i == focus_index
                row.update(render_stream_row(task, focused=is_focused))
                row.styles.display = "block"

                if is_focused:
                    row.add_class("focused")

                state = task.get("stream_state", "new")
                row.add_class(f"state-{state}")
            else:
                row.update("")
                row.styles.display = "none"

        # Auto-scroll to keep focused item visible
        self._scroll_to_focus(focus_index)

    def _scroll_to_focus(self, index: int):
        """Scroll the VerticalScroll to keep focused row visible."""
        try:
            scroll = self.query_one("#stream-scroll", VerticalScroll)
            row = self.query_one(f"#srow-{index}", Static)
            scroll.scroll_visible(row, animate=False)
        except Exception:
            pass

    def show_notification(self, message: str):
        """Show a notification bar at the top (auto-hidden by app timer)."""
        try:
            notif = self.query_one("#stream-notification", Static)
            notif.update(f"[#00D4AA]{message}[/]")
            notif.styles.display = "block"
        except Exception:
            pass

    def hide_notification(self):
        """Hide the notification bar."""
        try:
            notif = self.query_one("#stream-notification", Static)
            notif.styles.display = "none"
        except Exception:
            pass

    @property
    def focus_index(self) -> int:
        return self._focus_index

    @property
    def tasks(self) -> list[dict]:
        return self._tasks
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest brain/tests/test_command_centre/test_stream_list.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Syntax check the widget**

Run: `python3 -m py_compile brain/command_centre/stream_list.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add brain/command_centre/stream_list.py brain/tests/test_command_centre/test_stream_list.py
git commit -m "CC stream: add StreamList widget with row rendering"
```

---

## Chunk 3: App Integration — View Cycling + Stream Keys

### Task 5: Wire StreamList into app.py with view cycling

**Files:**
- Modify: `brain/command_centre/app.py`

- [ ] **Step 1: Add StreamList import and CSS**

At top of `app.py`, add import:
```python
from .stream_list import StreamList
from .bump import (
    bump_top, bump_back, mark_seen, snooze,
    undo_last, stream_sort_key, check_snoozed,
)
from .bump_persist import save_stream_state
from .task_loader import find_task_file
```

Add CSS rule after `#diagram-grid`:
```css
#stream-list {
    width: 3fr;
    display: none;
}
```

- [ ] **Step 2: Add StreamList to compose and update __init__**

In `compose()`, add before the TileGrid yield:
```python
yield StreamList(id="stream-list")
```

In `__init__()`, change `_view_mode` default and add undo stack:
```python
self._view_mode: str = "stream"  # Changed from "grid"
self._undo_stack: list[dict] = []
self._notification_timer = None
```

- [ ] **Step 3: Update _refresh_all for stream view**

In `_refresh_all()`, add a `"stream"` branch before the `"grid"` branch:

```python
if self._view_mode == "stream":
    stream = self.query_one("#stream-list", StreamList)
    grid.styles.display = "none"
    stream.styles.display = "block"
    focus_view.styles.display = "none"
    diagram_grid.styles.display = "none"

    # Sort tasks by stream sort key
    sorted_tasks = sorted(self.all_tasks, key=stream_sort_key)
    # Filter out snoozed
    visible = [t for t in sorted_tasks if t.get("stream_state") != "snoozed"]
    stream.update_items(visible, self.focus_index)
elif self._view_mode == "grid":
    stream.styles.display = "none"
    # ... existing grid code
```

Also get the `stream` widget reference at the top of the method alongside `grid`.

- [ ] **Step 4: Add view cycling with `v` key**

Add a `_cycle_view` method:
```python
def _cycle_view(self):
    """Cycle view: stream → grid → diagram → stream."""
    if self._view_mode == "stream":
        self._view_mode = "grid"
        self.focus_index = 0
        self.current_page = 0
    elif self._view_mode == "grid":
        if list_diagrams(DIAGRAMS_DIR):
            self._view_mode = "diagram"
            self._enter_diagram()
        else:
            self._view_mode = "stream"
            self.focus_index = 0
    elif self._view_mode == "diagram":
        self._view_mode = "stream"
        self.focus_index = 0
    self._refresh_all()
```

In `_handle_grid_key()`, replace the voice toggle binding for `v`:
```python
elif char == hk.get("cycle_view", "v"):
    self._cycle_view()
```

- [ ] **Step 5: Add `_handle_stream_key` method**

```python
def _handle_stream_key(self, key: str, char: str | None, hk: dict):
    """Handle keys in stream mode."""
    if key == "up":
        if self.focus_index > 0:
            self.focus_index -= 1
            self._panel_mode = "detail"
            self._refresh_all()
    elif key == "down":
        stream = self.query_one("#stream-list", StreamList)
        max_idx = len(stream.tasks) - 1
        if self.focus_index < max_idx:
            self.focus_index += 1
            self._panel_mode = "detail"
            self._refresh_all()
    elif key == "pageup":
        self.focus_index = max(0, self.focus_index - 10)
        self._refresh_all()
    elif key == "pagedown":
        stream = self.query_one("#stream-list", StreamList)
        max_idx = len(stream.tasks) - 1
        self.focus_index = min(max_idx, self.focus_index + 10)
        self._refresh_all()
    elif key == "home":
        self.focus_index = 0
        self._refresh_all()
    elif key == "end":
        stream = self.query_one("#stream-list", StreamList)
        self.focus_index = max(0, len(stream.tasks) - 1)
        self._refresh_all()
    elif key == "enter":
        self._stream_open_item()
    elif char == "t":
        self._stream_bump_top()
    elif char == "b":
        self._stream_bump_back()
    elif char == "s":
        self._stream_snooze()
    elif char == "z":
        self._stream_undo()
    elif char == hk.get("mark_done", "d"):
        self._mark_done()
    elif char == hk.get("cycle_view", "v"):
        self._cycle_view()
    elif char == hk.get("command_bar", "/"):
        self._open_command_palette()
    elif char == hk.get("chat_toggle", "c"):
        self._toggle_chat()
    elif char == hk.get("filter_mode", ":"):
        self._open_filter_picker()
    elif char == hk.get("help", "?"):
        self.push_screen(HelpOverlay())
```

Wire it into `on_key` dispatch — add before the grid handler:
```python
if self._view_mode == "stream":
    self._handle_stream_key(key, char, hk)
    return
```

- [ ] **Step 6: Add bump action methods**

```python
def _stream_bump_top(self):
    """Bump focused stream item to top."""
    task = self._focused_stream_task
    if not task:
        return
    bump_top(task, self._undo_stack)
    self._persist_stream_state(task)
    self.focus_index = 0
    self._refresh_all()

def _stream_bump_back(self):
    """Bump focused stream item to back."""
    task = self._focused_stream_task
    if not task:
        return
    bump_back(task, self._undo_stack)
    self._persist_stream_state(task)
    self._refresh_all()

def _stream_snooze(self):
    """Show snooze picker for focused item."""
    # For now, simple: prompt with 1h/tomorrow/next week
    # Using Textual notification as a quick picker
    self.notify(
        "Snooze: [bold]1[/]=1h  [bold]2[/]=tomorrow  [bold]3[/]=next week",
        timeout=5,
    )
    self._snooze_pending = True

def _stream_handle_snooze_choice(self, choice: str):
    """Handle snooze duration choice."""
    task = self._focused_stream_task
    if not task:
        return
    hours_map = {"1": 1, "2": 24, "3": 168}  # 1h, 24h, 7d
    hours = hours_map.get(choice)
    if hours:
        snooze(task, hours=hours, undo_stack=self._undo_stack)
        self._persist_stream_state(task)
        self._refresh_all()
    self._snooze_pending = False

def _stream_undo(self):
    """Undo last bump action."""
    if not self._undo_stack:
        self.notify("Nothing to undo")
        return
    # Find the task referenced by top of undo stack
    entry = self._undo_stack[-1]
    tid = entry["task_id"]
    for task in self.all_tasks:
        if task.get("id") == tid:
            undo_last(task, self._undo_stack)
            self._persist_stream_state(task)
            self._refresh_all()
            return
    self.notify(f"Task {tid} not found")

def _stream_open_item(self):
    """Open focused stream item in focus view, mark as seen."""
    task = self._focused_stream_task
    if not task:
        return
    mark_seen(task)
    self._persist_stream_state(task)
    self._enter_focus(task)

@property
def _focused_stream_task(self) -> dict | None:
    """Get the currently focused task in stream view."""
    try:
        stream = self.query_one("#stream-list", StreamList)
        tasks = stream.tasks
        if self.focus_index < len(tasks):
            return tasks[self.focus_index]
    except Exception:
        pass
    return None

def _persist_stream_state(self, task: dict):
    """Save stream state to task's markdown file."""
    path = find_task_file(task.get("id", ""))
    if path:
        save_stream_state(
            path,
            stream_state=task.get("stream_state", "new"),
            last_touched=task.get("last_touched", ""),
            snoozed_until=task.get("snoozed_until"),
        )
```

- [ ] **Step 7: Handle snooze keypresses in on_key**

In `_handle_stream_key`, at the very top before other key checks:
```python
# Handle pending snooze choice
if getattr(self, '_snooze_pending', False) and char in ("1", "2", "3"):
    self._stream_handle_snooze_choice(char)
    return
```

Add `self._snooze_pending = False` to `__init__`.

- [ ] **Step 8: Syntax check**

Run: `python3 -m py_compile brain/command_centre/app.py`
Expected: No errors

- [ ] **Step 9: Run all tests**

Run: `python3 -m pytest brain/tests/test_command_centre/ -x -q`
Expected: All tests PASS

- [ ] **Step 10: Commit**

```bash
git add brain/command_centre/app.py
git commit -m "CC stream: wire StreamList into app with view cycling and bump keys"
```

---

## Chunk 4: Status Bar + Context Panel + Chat Split

### Task 6: Stream-aware status bar

**Files:**
- Modify: `brain/command_centre/status_bar.py`

- [ ] **Step 1: Add stream hints constant**

Add after `_DIAGRAM_HINTS`:
```python
_STREAM_HINTS = (
    "[bold #FF6B35]Enter[/][dim] Open[/]  "
    "[bold #FF6B35]t[/][dim] Top[/]  "
    "[bold #FF6B35]b[/][dim] Back[/]  "
    "[bold #FF6B35]s[/][dim] Snooze[/]  "
    "[bold #FF6B35]d[/][dim] Done[/]  "
    "[bold #FF6B35]z[/][dim] Undo[/]  "
    "[bold #FF6B35]v[/][dim] View[/]  "
    "[bold #FF6B35]c[/][dim] Chat[/]  "
    "[bold #FF6B35]/[/][dim] Cmds[/]  "
    "[bold #FF6B35]:[/][dim] Filter[/]  "
    "[bold #FF6B35]?[/][dim] Help[/]"
)
```

- [ ] **Step 2: Add stream_counts parameter and stream branch**

In `update_counts()`, add parameters:
```python
stream_new: int = 0,
stream_back: int = 0,
stream_snoozed: int = 0,
```

Add view_mode check for "stream" before "grid":
```python
if view_mode == "stream":
    line1 = _STREAM_HINTS
    parts = [f"{total} items"]
    if stream_new:
        parts.append(f"[#00D4AA]{stream_new} new[/]")
    if stream_back:
        parts.append(f"[dim]{stream_back} back[/]")
    if stream_snoozed:
        parts.append(f"[#d4aa00]{stream_snoozed} snoozed[/]")
    # Append subsystem status
    if telegram_status:
        parts.append(f"[bold #00D4AA]{telegram_status}[/]")
    if heartbeat_status:
        parts.append(f"[bold #FF6B35]{heartbeat_status}[/]")
    parts.append("Stream View")
    line2 = " │ ".join(parts)
    self.update(f"{line1}\n{line2}")
    return
```

- [ ] **Step 3: Update app.py _refresh_all to pass stream counts**

In the status bar update section of `_refresh_all()`, add a stream branch:
```python
if self._view_mode == "stream":
    new_count = sum(1 for t in self.all_tasks if t.get("stream_state") == "new")
    back_count = sum(1 for t in self.all_tasks if t.get("stream_state") == "back")
    snoozed_count = sum(1 for t in self.all_tasks if t.get("stream_state") == "snoozed")
    status.update_counts(
        total=len(self.all_tasks),
        view_mode="stream",
        stream_new=new_count,
        stream_back=back_count,
        stream_snoozed=snoozed_count,
        telegram_status=self.telegram.status_label,
        heartbeat_status=self.heartbeat.status_label,
    )
```

- [ ] **Step 4: Syntax check both files**

Run: `python3 -m py_compile brain/command_centre/status_bar.py && python3 -m py_compile brain/command_centre/app.py`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add brain/command_centre/status_bar.py brain/command_centre/app.py
git commit -m "CC stream: stream-aware status bar with new/back/snoozed counts"
```

---

### Task 7: Chat split layout

**Files:**
- Modify: `brain/command_centre/app.py` (CSS + toggle logic)
- Modify: `brain/command_centre/context_panel.py` (chat header update)

- [ ] **Step 1: Add CSS for stream chat split**

In the app CSS, add:
```css
#stream-list.chat-active {
    width: 1fr;
    opacity: 0.3;
}
```

And update context panel CSS to expand in chat+stream mode — modify the ContextPanel DEFAULT_CSS to add:
```css
ContextPanel.chat-hero {
    width: 2.5fr;
}
```

- [ ] **Step 2: Update _toggle_chat for stream view**

Modify `_toggle_chat()` in app.py to handle stream split:
```python
def _toggle_chat(self):
    """Toggle chat mode — in stream view, use split layout."""
    try:
        panel = self.query_one("#context-panel", ContextPanel)
        if panel.is_chat_mode:
            # Closing chat — restore widths
            panel.toggle_mode()
            if self._view_mode == "stream":
                stream = self.query_one("#stream-list", StreamList)
                stream.remove_class("chat-active")
                panel.remove_class("chat-hero")
            self.notify("Chat mode OFF")
            self._refresh_all()
        else:
            # Opening chat
            panel.toggle_mode()
            if self._view_mode == "stream":
                stream = self.query_one("#stream-list", StreamList)
                stream.add_class("chat-active")
                panel.add_class("chat-hero")
            self.notify("Chat mode ON")
    except Exception:
        pass
```

- [ ] **Step 3: Update chat header to show "CHATTING ABOUT"**

In `context_panel.py` `_render_chat_header()`, update to show focused task context:
```python
# If task context available, show "CHATTING ABOUT" header
if self._task_context:
    task = self._task_context[0]
    title = sanitise(task.get("title", "")).replace("[", r"\[")
    if len(title) > 40:
        title = title[:37] + "..."
    tid = task.get("id", "")
    lines += f"[bold #FF6B35]CHATTING ABOUT[/]\n"
    lines += f"[bold]{title}[/] [dim]· {tid}[/]\n"
```

- [ ] **Step 4: Syntax check**

Run: `python3 -m py_compile brain/command_centre/app.py && python3 -m py_compile brain/command_centre/context_panel.py`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add brain/command_centre/app.py brain/command_centre/context_panel.py
git commit -m "CC stream: split chat layout with dimmed stream + CHATTING ABOUT header"
```

---

## Chunk 5: Notification Bar + Proactive Polling

### Task 8: Notification bar on new items

**Files:**
- Modify: `brain/command_centre/app.py`

- [ ] **Step 1: Add notification helper methods**

```python
def _show_stream_notification(self, message: str):
    """Show a notification in the stream widget that auto-hides after 3s."""
    if self._view_mode != "stream":
        return
    try:
        stream = self.query_one("#stream-list", StreamList)
        stream.show_notification(message)
        # Cancel previous timer if any
        if self._notification_timer is not None:
            self._notification_timer.stop()
        self._notification_timer = self.set_timer(3.0, self._hide_stream_notification)
    except Exception:
        pass

def _hide_stream_notification(self):
    """Hide the stream notification bar."""
    try:
        stream = self.query_one("#stream-list", StreamList)
        stream.hide_notification()
    except Exception:
        pass
    self._notification_timer = None
```

- [ ] **Step 2: Syntax check**

Run: `python3 -m py_compile brain/command_centre/app.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add brain/command_centre/app.py
git commit -m "CC stream: add notification bar with 3s auto-fade"
```

---

### Task 9: Proactive email + reminder polling in heartbeat

**Files:**
- Modify: `brain/command_centre/heartbeat_bridge.py`
- Modify: `brain/command_centre/app.py`

- [ ] **Step 1: Add email/reminder polling to heartbeat processing**

In `heartbeat_bridge.py`, add an `_on_poll_callback` to the constructor and a polling method:

```python
def __init__(self):
    # ... existing fields ...
    self._on_new_items = None  # Callback: async fn(message: str)

async def start(self, on_notification=None, on_new_items=None) -> bool:
    self._on_notification = on_notification
    self._on_new_items = on_new_items
    # ... rest unchanged ...
```

Add to `_process_heartbeat()` after the existing reminders check:

```python
# Proactive email + reminder polling
await self._poll_for_new_items()
```

Add the polling method:
```python
async def _poll_for_new_items(self):
    """Check for new emails and reminders, notify if found."""
    messages = []

    # Email check (with timeout protection)
    try:
        from brain.core.config import Config
        from brain.mail.inbox import Inbox

        config = Config.load()
        if config.email_address and config.email_app_password:
            inbox = Inbox(config.email_address, config.email_app_password)
            emails = await inbox.check(limit=5, unread_only=True)
            if emails:
                messages.append(f"✉ {len(emails)} new email{'s' if len(emails) != 1 else ''}")
    except Exception as e:
        logger.warning("Email poll failed: %s", e)

    if messages and self._on_new_items:
        await self._on_new_items(" · ".join(messages))
```

- [ ] **Step 2: Wire polling callback in app.py**

In `_init_heartbeat()`, pass the new callback:

```python
async def _init_heartbeat(self):
    success = await self.heartbeat.start(
        on_notification=self._on_heartbeat_notification,
        on_new_items=self._on_new_items_arrived,
    )
    # ...

async def _on_new_items_arrived(self, message: str):
    """Called by heartbeat when new emails/reminders found."""
    self.all_tasks = load_tasks()
    self._show_stream_notification(message)
    self._refresh_all()
```

- [ ] **Step 3: Syntax check**

Run: `python3 -m py_compile brain/command_centre/heartbeat_bridge.py && python3 -m py_compile brain/command_centre/app.py`
Expected: No errors

- [ ] **Step 4: Run all tests**

Run: `python3 -m pytest brain/tests/test_command_centre/ -x -q`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add brain/command_centre/heartbeat_bridge.py brain/command_centre/app.py
git commit -m "CC stream: proactive email polling via heartbeat with notification"
```

---

## Chunk 6: Help System + Final Polish

### Task 10: Update help system

**Files:**
- Modify: `brain/command_centre/help_data.yml`

- [ ] **Step 1: Add stream keys to help_data.yml**

Add a new section for stream view keys. Check existing format first:
Run: `head -30 brain/command_centre/help_data.yml`

Then add stream view hotkeys following the same YAML format.

- [ ] **Step 2: Regenerate help outputs**

Run: `python3 -m brain.command_centre.help_gen`
Expected: HELP.md and app.py _HELP_TEXT updated

- [ ] **Step 3: Verify help sync**

Run: `python3 -m brain.command_centre.help_gen --check`
Expected: "Help outputs are up to date"

- [ ] **Step 4: Commit**

```bash
git add brain/command_centre/help_data.yml brain/command_centre/app.py docs/HELP.md
git commit -m "CC stream: update help system with stream view keys"
```

---

### Task 11: Update _focused_task property for stream view

**Files:**
- Modify: `brain/command_centre/app.py`

- [ ] **Step 1: Update _focused_task to handle stream view**

Modify the `_focused_task` property (around line 327):

```python
@property
def _focused_task(self) -> dict | None:
    """Get the currently focused task (stream, grid, or focus view)."""
    if self._view_mode == "focus":
        try:
            fv = self.query_one("#task-focus", TaskFocusView)
            return fv.task
        except Exception:
            return None
    if self._view_mode == "stream":
        return self._focused_stream_task
    if self.focus_index < len(self.page_tasks):
        return self.page_tasks[self.focus_index]
    return None
```

- [ ] **Step 2: Syntax check**

Run: `python3 -m py_compile brain/command_centre/app.py`

- [ ] **Step 3: Commit**

```bash
git add brain/command_centre/app.py
git commit -m "CC stream: fix _focused_task for stream view mode"
```

---

### Task 12: Final integration test

**Files:**
- None (manual testing)

- [ ] **Step 1: Run full test suite**

Run: `python3 -m pytest brain/tests/test_command_centre/ -x -q`
Expected: All tests PASS

- [ ] **Step 2: Run inbox tests**

Run: `python3 -m pytest brain/tests/unit/test_inbox.py -x -q`
Expected: All tests PASS

- [ ] **Step 3: Syntax check all modified files**

```bash
python3 -m py_compile brain/command_centre/app.py
python3 -m py_compile brain/command_centre/stream_list.py
python3 -m py_compile brain/command_centre/bump.py
python3 -m py_compile brain/command_centre/bump_persist.py
python3 -m py_compile brain/command_centre/task_loader.py
python3 -m py_compile brain/command_centre/status_bar.py
python3 -m py_compile brain/command_centre/context_panel.py
python3 -m py_compile brain/command_centre/heartbeat_bridge.py
```

- [ ] **Step 4: Launch CC and verify**

Run: `python3 -m brain.command_centre`

Verify:
- Stream view is the default (not grid)
- ↑/↓ navigates items
- `t` bumps to top (item becomes NEW at position 1)
- `b` bumps to back (item becomes BACK at bottom)
- `s` shows snooze picker, `1`/`2`/`3` selects duration
- `z` undoes last action
- `v` cycles to grid view, then back to stream
- `c` opens chat with split layout (stream dims to 30%)
- Enter opens focus view, item marked as SEEN on return
- Status bar shows stream hints + counts

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "CC stream: integration polish and verification"
git push
```
