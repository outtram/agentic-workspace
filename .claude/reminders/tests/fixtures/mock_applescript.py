from datetime import datetime
from typing import Optional


class MockAppleScriptAdapter:
    """Mock Reminders.app for testing without real app"""

    def __init__(self):
        self.reminders: dict[str, dict] = {}
        self.call_log: list[tuple] = []
        self._next_id = 1

    def create_reminder(
        self,
        name: str,
        body: str = "",
        tags: Optional[list[str]] = None,
        due_date: Optional[str] = None,
        priority: int = 0,
        list_name: str = "Reminders"
    ) -> str:
        """Create reminder and return ID"""
        reminder_id = f"mock-reminder-{self._next_id}"
        self._next_id += 1

        self.reminders[reminder_id] = {
            "id": reminder_id,
            "name": name,
            "body": body,
            "tags": tags or [],
            "due_date": due_date,
            "priority": priority,
            "list": list_name,
            "completed": False,
            "modified": datetime.now()
        }

        self.call_log.append(("create", name, list_name))
        return reminder_id

    def update_reminder(self, reminder_id: str, **changes):
        """Update reminder fields"""
        if reminder_id not in self.reminders:
            raise ValueError(f"Reminder {reminder_id} not found")

        self.reminders[reminder_id].update(changes)
        self.reminders[reminder_id]["modified"] = datetime.now()
        self.call_log.append(("update", reminder_id))

    def delete_reminder(self, reminder_id: str):
        """Delete reminder"""
        if reminder_id not in self.reminders:
            raise ValueError(f"Reminder {reminder_id} not found")

        del self.reminders[reminder_id]
        self.call_log.append(("delete", reminder_id))

    def fetch_all_reminders(self) -> list[dict]:
        """Fetch all active reminders"""
        self.call_log.append(("fetch_all",))
        return [r for r in self.reminders.values() if not r["completed"]]

    def get_reminder(self, reminder_id: str) -> Optional[dict]:
        """Get single reminder by ID"""
        return self.reminders.get(reminder_id)
