"""Bridge to existing AAGLOBAL reminders system."""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_due_reminders() -> list[dict]:
    """Get due/overdue reminders from the existing reminders CLI.

    Returns list of dicts with keys: id, title, due_date, priority, status
    """
    # Add reminders path to sys.path if needed
    reminders_path = Path(__file__).resolve().parents[3] / ".claude" / "reminders"
    if str(reminders_path) not in sys.path:
        sys.path.insert(0, str(reminders_path))

    try:
        from core.manager import RemindersManager

        manager = RemindersManager()
        items = manager.list_items(status="todo")

        due = []
        for item in items:
            if item.due_date:
                due.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "due_date": item.due_date,
                        "priority": item.priority,
                        "status": item.status,
                        "eisenhower": getattr(item, "eisenhower_quadrant", None),
                    }
                )
        return due
    except Exception as e:
        logger.error("Failed to get reminders: %s", e)
        return []


def format_reminders_for_judge(reminders: list[dict]) -> str:
    """Format reminders into a readable string for the importance judge."""
    if not reminders:
        return "No due reminders."

    lines = ["*Due/Upcoming Reminders:*"]
    for r in reminders:
        priority = f" [{r['priority']}]" if r.get("priority") else ""
        due = f" (due: {r['due_date']})" if r.get("due_date") else ""
        lines.append(f"  {r['title']}{priority}{due}")

    return "\n".join(lines)
