"""Daily review workflow — pure Python, no shell execution required.

Runs the full daily pipeline: sync reminders, generate dashboard, check overdue.
Callable from OutBot CLI, Telegram, or any Python context.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Add .claude dir and reminders venv site-packages to path
_claude_dir = Path(__file__).resolve().parents[2] / ".claude"
if str(_claude_dir) not in sys.path:
    sys.path.insert(0, str(_claude_dir))

# The reminders package has its own venv with pyyaml etc.
_reminders_venv_sp = _claude_dir / "reminders" / ".venv" / "lib"
if _reminders_venv_sp.exists():
    # Find the python3.X directory inside lib/
    for sp_dir in _reminders_venv_sp.iterdir():
        site_packages = sp_dir / "site-packages"
        if site_packages.exists() and str(site_packages) not in sys.path:
            sys.path.insert(0, str(site_packages))
            break


def _get_manager():
    """Get a RemindersManager instance."""
    from reminders.core.manager import RemindersManager
    return RemindersManager()


def sync_reminders() -> dict:
    """Import new reminders from macOS Reminders.app.

    Returns dict with keys: new, skipped, quadrants.
    """
    manager = _get_manager()

    try:
        reminders = manager.applescript.fetch_all_reminders()
    except Exception as e:
        logger.error("Failed to fetch reminders: %s", e)
        return {"new": 0, "skipped": 0, "quadrants": {}, "error": str(e)}

    if not reminders:
        return {"new": 0, "skipped": 0, "quadrants": {}}

    existing = manager.list_reminders()
    existing_ids = {item.reminder_id for item in existing if item.reminder_id}

    new_count = 0
    skipped = 0
    quadrants = {"q1": 0, "q2": 0, "q3": 0, "q4": 0}

    for reminder in reminders:
        if reminder["id"] in existing_ids:
            skipped += 1
            continue

        work_item = manager.import_reminder(
            title=reminder["name"],
            reminder_id=reminder["id"],
            due_date=reminder["due_date"],
            tags=reminder["tags"],
            priority=manager._map_apple_priority_to_string(reminder["priority"]),
            description=reminder["body"],
            list_name=reminder["list"],
        )
        quadrants[work_item.eisenhower_quadrant] += 1
        new_count += 1

    return {"new": new_count, "skipped": skipped, "quadrants": quadrants}


def get_quadrant_counts() -> dict:
    """Count tasks by Eisenhower quadrant. Returns {q1: n, q2: n, ...}."""
    manager = _get_manager()
    all_items = manager.list_reminders(status="todo")
    counts = {"q1": 0, "q2": 0, "q3": 0, "q4": 0}
    for item in all_items:
        q = item.eisenhower_quadrant
        if q in counts:
            counts[q] += 1
    return counts


def get_overdue_tasks() -> dict:
    """Find overdue, due-today, and due-soon Q1 tasks.

    Returns dict with keys: overdue, due_today, due_soon (each a list of dicts).
    """
    manager = _get_manager()
    q1_items = manager.list_reminders(quadrant="q1", status="todo")
    today = datetime.now().date()

    overdue = []
    due_today = []
    due_soon = []

    for item in q1_items:
        if not item.due_date:
            continue
        try:
            due_str = item.due_date
            if "T" in due_str:
                due = datetime.fromisoformat(due_str.replace("Z", "+00:00")).date()
            else:
                due = datetime.fromisoformat(due_str).date()
            days = (due - today).days

            entry = {"id": item.id, "title": item.title, "due_date": due_str, "days": days}
            if days < 0:
                entry["days_overdue"] = abs(days)
                overdue.append(entry)
            elif days == 0:
                due_today.append(entry)
            elif days <= 3:
                due_soon.append(entry)
        except (ValueError, AttributeError):
            continue

    overdue.sort(key=lambda x: x["days_overdue"], reverse=True)
    return {"overdue": overdue, "due_today": due_today, "due_soon": due_soon}


def generate_dashboard() -> dict:
    """Generate the Eisenhower HTML dashboard and update the mobile gist.

    Returns dict with keys: filepath, gist_updated, counts.
    """
    import importlib.util

    # Import generate-dashboard.py (hyphenated filename can't use normal import)
    script_path = _claude_dir / "scripts" / "generate-dashboard.py"
    spec = importlib.util.spec_from_file_location("generate_dashboard", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    tasks = mod.scan_work_items()
    filepath, q1, q2, q3, q4 = mod.generate_dashboard(tasks)
    gist_ok = mod.update_gist(filepath)

    return {
        "filepath": str(filepath),
        "gist_updated": gist_ok,
        "counts": {"q1": q1, "q2": q2, "q3": q3, "q4": q4},
    }


def run_daily_review() -> str:
    """Run the full daily review and return a formatted summary string."""
    # Step 1: Sync reminders
    sync = sync_reminders()

    # Step 2: Get current quadrant counts
    counts = get_quadrant_counts()
    total = sum(counts.values())

    # Step 3: Check overdue
    urgency = get_overdue_tasks()

    # Step 4: Generate dashboard
    dash = {}
    try:
        dash = generate_dashboard()
    except Exception as e:
        logger.error("Dashboard generation failed: %s", e)
        dash = {"filepath": None, "gist_updated": False, "error": str(e)}

    # Build summary
    lines = ["Daily Review Complete\n"]

    # Sync results
    if sync.get("error"):
        lines.append(f"Reminders sync failed: {sync['error']}")
    else:
        lines.append(f"Imported: {sync['new']} new reminders ({sync['skipped']} duplicates skipped)")

    # Quadrant counts
    lines.append(f"\nCurrent workload: {total} tasks")
    lines.append(f"  Q1 (Do First): {counts['q1']}")
    lines.append(f"  Q2 (Schedule): {counts['q2']}")
    lines.append(f"  Q3 (Delegate): {counts['q3']}")
    lines.append(f"  Q4 (Eliminate): {counts['q4']}")

    # Overdue warnings
    if urgency["overdue"]:
        lines.append(f"\nOVERDUE ({len(urgency['overdue'])} tasks):")
        for t in urgency["overdue"][:5]:
            lines.append(f"  {t['id']}: {t['title']} ({t['days_overdue']} days overdue)")

    if urgency["due_today"]:
        lines.append(f"\nDUE TODAY ({len(urgency['due_today'])} tasks):")
        for t in urgency["due_today"]:
            lines.append(f"  {t['id']}: {t['title']}")

    if urgency["due_soon"]:
        lines.append(f"\nDUE SOON ({len(urgency['due_soon'])} tasks):")
        for t in urgency["due_soon"]:
            lines.append(f"  {t['id']}: {t['title']} (in {t['days']} days)")

    # Dashboard
    if dash.get("filepath"):
        lines.append(f"\nDashboard: {dash['filepath']}")
        if dash.get("gist_updated"):
            lines.append("Mobile: https://gist.githack.com/outtram/20f5befb1e2f8cef427b784e6860ddf8/raw/eisenhower-dashboard.html")
        else:
            lines.append("Mobile gist update failed")
    elif dash.get("error"):
        lines.append(f"\nDashboard failed: {dash['error']}")

    return "\n".join(lines)
