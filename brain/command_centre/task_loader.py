"""Task loading, sorting, and today list management.

Extracted from .claude/scripts/task-picker.py for reuse in Command Centre.
"""
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import yaml

from . import PROJECT_ROOT

_TASK_DIR = PROJECT_ROOT / ".claude" / "work" / "tasks"
_DASHBOARD_DIR = PROJECT_ROOT / ".claude" / "dashboards"
_TODAY_FILE = _DASHBOARD_DIR / "today.yml"

QUADRANT_WEIGHT = {"q1": 4, "q2": 3, "q3": 2, "q4": 1}
QUADRANT_COLOURS = {
    "q1": "#FF6B35",
    "q2": "#00D4AA",
    "q3": "#777777",
    "q4": "#3D3D3D",
}
QUADRANT_LABELS = {
    "q1": "Q1",
    "q2": "Q2",
    "q3": "Q3",
    "q4": "Q4",
}


def _parse_task_file(path: Path) -> Optional[dict]:
    """Read a task markdown file with YAML frontmatter."""
    text = path.read_text()
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None

    body = parts[2].strip()
    desc_lines = []
    in_desc = False
    for line in body.split("\n"):
        if line.startswith("## Description"):
            in_desc = True
            continue
        if in_desc:
            if line.startswith("##"):
                break
            desc_lines.append(line)
    meta["_description"] = "\n".join(desc_lines).strip()
    meta["_file"] = path.name
    return meta


def load_tasks() -> list[dict]:
    """Read, weight, and sort all active tasks."""
    tasks = []
    today = date.today()

    for f in sorted(_TASK_DIR.glob("OUT-*.md")):
        t = _parse_task_file(f)
        if t is None or t.get("status") not in ("todo", "open", "draft"):
            continue

        q = t.get("eisenhower_quadrant", "q4")
        weight = QUADRANT_WEIGHT.get(q, 1)

        due = t.get("due_date")
        if due:
            try:
                if isinstance(due, str) and due:
                    due_date = datetime.fromisoformat(due).date()
                elif isinstance(due, date):
                    due_date = due
                else:
                    due_date = None
            except (ValueError, TypeError):
                due_date = None

            if due_date:
                days_until = (due_date - today).days
                if days_until < 0:
                    weight += 3
                    t["_overdue"] = True
                elif days_until == 0:
                    weight += 2
                    t["_due_today"] = True
                elif days_until <= 3:
                    weight += 1
                t["_due_date"] = due_date

        t["_weight"] = weight
        tasks.append(t)

    tasks.sort(key=lambda t: t["_weight"], reverse=True)
    return tasks


def load_today_list() -> list[str]:
    """Load previously saved today list."""
    if _TODAY_FILE.exists():
        try:
            data = yaml.safe_load(_TODAY_FILE.read_text())
            if isinstance(data, dict):
                return data.get("tasks", [])
        except yaml.YAMLError:
            pass
    return []


def save_today_list(task_ids: list[str]):
    """Save today list to YAML."""
    _DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "date": date.today().isoformat(),
        "updated": datetime.now().isoformat(),
        "tasks": task_ids,
    }
    _TODAY_FILE.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
