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
    """Sort key: state group (NEW < SEEN < BACK), then newest first."""
    state = task.get("stream_state", STREAM_NEW)
    order = _STATE_ORDER.get(state, 0)
    last_touched = task.get("last_touched", "")
    return (order, "" if not last_touched else _invert_timestamp(last_touched))


def _invert_timestamp(iso: str) -> str:
    """Invert ISO timestamp for descending sort within ascending key."""
    return "".join(chr(126 - ord(c)) if c.isdigit() else c for c in iso)
