from datetime import datetime
from reminders.core.models import WorkItem, Reminder

def test_work_item_creation():
    """Should create WorkItem with all fields"""
    work_item = WorkItem(
        id="OUT-264",
        title="Call Leon",
        status="todo",
        priority="high",
        due_date="2026-02-14",
        tags=["phone", "urgent"],
        tag_categories={"context": ["phone"], "priority": ["urgent"]},
        eisenhower_quadrant="q1",
        eisenhower_urgent=True,
        eisenhower_important=True,
        source="reminder",
        reminder_id="x-apple-reminder://ABC123",
        reminder_list="Reminders",
        description="Discuss equity partner timeline",
        updated=datetime.now()
    )

    assert work_item.id == "OUT-264"
    assert work_item.title == "Call Leon"
    assert "phone" in work_item.tags
    assert work_item.eisenhower_quadrant == "q1"

def test_reminder_creation():
    """Should create Reminder with all fields"""
    reminder = Reminder(
        id="x-apple-reminder://ABC123",
        name="Call Leon",
        body="Discuss equity partner timeline",
        tags=["phone", "urgent"],
        due_date=datetime(2026, 2, 14),
        priority=1,
        list_name="Reminders",
        completed=False
    )

    assert reminder.id == "x-apple-reminder://ABC123"
    assert reminder.name == "Call Leon"
    assert reminder.priority == 1
    assert not reminder.completed
