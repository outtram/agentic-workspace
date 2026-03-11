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
