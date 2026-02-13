from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class WorkItem:
    """Represents a work item (task/bug) in the file-native system"""
    id: str
    title: str
    status: str = "todo"
    priority: str = "low"
    due_date: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    tag_categories: dict[str, list[str]] = field(default_factory=dict)
    eisenhower_quadrant: str = "q4"
    eisenhower_urgent: bool = False
    eisenhower_important: bool = False
    source: str = "manual"
    reminder_id: Optional[str] = None
    reminder_list: Optional[str] = None
    branch: Optional[str] = None
    description: str = ""
    steps: list[str] = field(default_factory=list)
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    def __post_init__(self):
        """Generate branch name if not provided"""
        if not self.branch and self.id:
            clean_title = self.title.lower()[:30].replace(" ", "-")
            self.branch = f"task/{self.id}-{clean_title}"

@dataclass
class Reminder:
    """Represents a reminder from Reminders.app via AppleScript"""
    id: str
    name: str
    body: str = ""
    tags: list[str] = field(default_factory=list)
    due_date: Optional[datetime] = None
    priority: int = 0  # 0=none, 1=high, 5=medium, 9=low
    list_name: str = "Reminders"
    completed: bool = False
    modified: Optional[datetime] = None
