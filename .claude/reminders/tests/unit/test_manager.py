import pytest
from datetime import datetime
from reminders.core.manager import RemindersManager
from reminders.core.events import EventBus, WorkItemCreated, WorkItemCompleted, WorkItemDeleted
from reminders.tests.fixtures.mock_applescript import MockAppleScriptAdapter
from pathlib import Path


@pytest.fixture
def temp_work_dir(tmp_path):
    work_dir = tmp_path / "work" / "tasks"
    work_dir.mkdir(parents=True)
    return work_dir


@pytest.fixture
def manager(temp_work_dir):
    """Create RemindersManager with mock dependencies"""
    bus = EventBus()
    applescript = MockAppleScriptAdapter()
    return RemindersManager(
        event_bus=bus,
        applescript_adapter=applescript,
        work_dir=temp_work_dir
    )


def test_create_reminder_creates_work_item_and_pushes(manager, temp_work_dir):
    """Should create work item file and push to Reminders.app"""
    work_item = manager.create_reminder(
        title="Call Leon",
        due_date="2026-02-14",
        tags=["phone", "urgent"],
        priority="high"
    )

    # Check work item created
    assert work_item.id.startswith("OUT-")
    assert work_item.title == "Call Leon"
    assert "phone" in work_item.tags

    # Check file created
    files = list(temp_work_dir.glob("OUT-*.md"))
    assert len(files) == 1

    # Check pushed to Reminders.app (mock)
    assert len(manager.applescript.call_log) == 1
    assert manager.applescript.call_log[0][0] == "create"


def test_create_reminder_emits_event(manager):
    """Should emit WorkItemCreated event"""
    events = []
    manager.event_bus.subscribe(WorkItemCreated, lambda e: events.append(e))

    work_item = manager.create_reminder("Test task")

    assert len(events) == 1
    assert events[0].work_item_id == work_item.id


def test_complete_reminder(manager):
    """Should mark work item and reminder as completed"""
    work_item = manager.create_reminder("Test task")

    manager.complete_reminder(work_item.id)

    # Check work item updated
    updated_item = manager.get_reminder(work_item.id)
    assert updated_item.status == "done"

    # Check Reminders.app updated
    reminder = manager.applescript.get_reminder(work_item.reminder_id)
    assert reminder["completed"] is True


def test_complete_reminder_emits_event(manager):
    """Should emit WorkItemCompleted event"""
    events = []
    manager.event_bus.subscribe(WorkItemCompleted, lambda e: events.append(e))

    work_item = manager.create_reminder("Test task")
    manager.complete_reminder(work_item.id)

    assert len(events) == 1
    assert events[0].work_item_id == work_item.id


def test_delete_reminder(manager, temp_work_dir):
    """Should delete from both systems"""
    work_item = manager.create_reminder("Test task")

    manager.delete_reminder(work_item.id)

    # Check work item deleted
    assert manager.get_reminder(work_item.id) is None

    # Check file deleted
    files = list(temp_work_dir.glob("OUT-*.md"))
    assert len(files) == 0


def test_delete_reminder_emits_event(manager):
    """Should emit WorkItemDeleted event"""
    events = []
    manager.event_bus.subscribe(WorkItemDeleted, lambda e: events.append(e))

    work_item = manager.create_reminder("Test task")
    manager.delete_reminder(work_item.id)

    assert len(events) == 1
    assert events[0].work_item_id == work_item.id


def test_list_reminders_with_filters(manager):
    """Should filter reminders by tags and quadrant"""
    manager.create_reminder("Task 1", tags=["aussuper"], priority="high")
    manager.create_reminder("Task 2", tags=["phone"], priority="low")
    manager.create_reminder("Task 3", tags=["aussuper", "phone"], priority="high")

    # Filter by tag
    aussuper_items = manager.list_reminders(tags=["aussuper"])
    assert len(aussuper_items) == 2

    # Filter by quadrant
    q1_items = manager.list_reminders(quadrant="q1")
    assert all(item.eisenhower_quadrant == "q1" for item in q1_items)


def test_get_reminder(manager):
    """Should return single work item by ID"""
    work_item = manager.create_reminder("Test task")

    result = manager.get_reminder(work_item.id)
    assert result is not None
    assert result.id == work_item.id
    assert result.title == "Test task"


def test_get_reminder_not_found(manager):
    """Should return None for non-existent ID"""
    result = manager.get_reminder("OUT-999")
    assert result is None


def test_create_reminder_eisenhower_classification(manager):
    """Should classify into correct Eisenhower quadrant"""
    # Q1: urgent (has due date) + important (high priority)
    q1 = manager.create_reminder("Q1 task", due_date="2026-02-14", priority="high")
    assert q1.eisenhower_quadrant == "q1"
    assert q1.eisenhower_urgent is True
    assert q1.eisenhower_important is True

    # Q2: not urgent (no due date) + important (high priority)
    q2 = manager.create_reminder("Q2 task", priority="high")
    assert q2.eisenhower_quadrant == "q2"

    # Q4: not urgent + not important
    q4 = manager.create_reminder("Q4 task", priority="low")
    assert q4.eisenhower_quadrant == "q4"


def test_create_multiple_reminders_unique_ids(manager):
    """Should generate unique sequential IDs"""
    item1 = manager.create_reminder("Task 1")
    item2 = manager.create_reminder("Task 2")
    item3 = manager.create_reminder("Task 3")

    assert item1.id != item2.id
    assert item2.id != item3.id

    # IDs should be sequential
    num1 = int(item1.id.split("-")[1])
    num2 = int(item2.id.split("-")[1])
    num3 = int(item3.id.split("-")[1])
    assert num2 == num1 + 1
    assert num3 == num2 + 1
