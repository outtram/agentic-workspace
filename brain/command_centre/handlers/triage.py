"""Triage handlers — /done, /today, /remove, /q1-q4."""
import sys

import yaml

from .. import PROJECT_ROOT
from ..brain_logger import log_action

_TASK_DIR = PROJECT_ROOT / ".claude" / "work" / "tasks"


async def handle_done(task_ids: list[str]) -> str:
    """Mark tasks as done via RemindersManager (local + iOS + git)."""
    if not task_ids:
        return "No tasks selected"

    sys.path.insert(0, str(PROJECT_ROOT / ".claude"))
    from reminders.core.manager import RemindersManager

    manager = RemindersManager()
    completed = 0
    for tid in task_ids:
        try:
            manager.complete_reminder(tid)
            completed += 1
        except Exception:
            pass

    log_action("done", task_ids=task_ids)
    return f"Completed {completed} task{'s' if completed != 1 else ''}"


def handle_today(task_ids: list[str], today_ids: list[str]) -> str:
    """Add tasks to today list."""
    if not task_ids:
        return "No tasks selected"

    added = 0
    for tid in task_ids:
        if tid not in today_ids:
            today_ids.append(tid)
            added += 1

    log_action("added_to_today", task_ids=task_ids)
    return f"Added {added} to today"


def handle_remove(task_ids: list[str], today_ids: list[str]) -> str:
    """Remove tasks from today list."""
    if not task_ids:
        return "No tasks selected"

    removed = 0
    for tid in task_ids:
        if tid in today_ids:
            today_ids.remove(tid)
            removed += 1

    log_action("removed_from_today", task_ids=task_ids)
    return f"Removed {removed} from today"


def _update_task_quadrant(task_id: str, quadrant: str):
    """Update a task's Eisenhower quadrant in its file."""
    task_file = _TASK_DIR / f"{task_id}.md"
    if not task_file.exists():
        return

    content = task_file.read_text()
    parts = content.split("---", 2)
    if len(parts) < 3:
        return

    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return
    if not isinstance(meta, dict):
        return

    meta["eisenhower_quadrant"] = quadrant
    meta["eisenhower_urgent"] = quadrant in ("q1", "q3")
    meta["eisenhower_important"] = quadrant in ("q1", "q2")

    new_frontmatter = yaml.dump(meta, default_flow_style=False, sort_keys=False)
    task_file.write_text(f"---\n{new_frontmatter}---{parts[2]}")


async def handle_quadrant(quadrant: str, task_ids: list[str]) -> str:
    """Move tasks to a different Eisenhower quadrant."""
    if not task_ids:
        return "No tasks selected"

    moved = 0
    for tid in task_ids:
        try:
            _update_task_quadrant(tid, quadrant)
            moved += 1
        except Exception:
            pass

    log_action("quadrant_move", task_ids=task_ids, context=quadrant)
    return f"Moved {moved} to {quadrant.upper()}"
