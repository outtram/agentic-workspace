import pytest
from reminders.core.manager import RemindersManager
from reminders.core.events import EventBus, WorkItemCompleted
from reminders.tests.fixtures.mock_applescript import MockAppleScriptAdapter
from pathlib import Path


@pytest.fixture
def temp_work_dir(tmp_path):
    work_dir = tmp_path / "work" / "tasks"
    work_dir.mkdir(parents=True)
    return work_dir


@pytest.fixture
def manager(temp_work_dir):
    bus = EventBus()
    applescript = MockAppleScriptAdapter()
    return RemindersManager(
        event_bus=bus,
        applescript_adapter=applescript,
        work_dir=temp_work_dir
    )


def _import_task(manager, title, reminder_id):
    """Helper to import a task with a given reminder_id."""
    return manager.import_reminder(
        title=title,
        reminder_id=reminder_id,
        priority="low",
    )


def test_marks_stale_tasks_as_done(manager):
    """Tasks whose iOS reminder is gone should be marked done."""
    item = _import_task(manager, "Stale task", "ios-111")
    assert item is not None

    stale = manager.reverse_sync(active_ios_reminder_ids=set())
    assert stale == [item.id]

    updated = manager.get_reminder(item.id)
    assert updated.status == "done"


def test_dry_run_returns_ids_without_updating(manager):
    """Dry run should identify stale tasks but not change status."""
    item = _import_task(manager, "Dry run task", "ios-222")

    stale = manager.reverse_sync(active_ios_reminder_ids=set(), dry_run=True)
    assert stale == [item.id]

    updated = manager.get_reminder(item.id)
    assert updated.status == "todo"


def test_ignores_already_done_tasks(manager):
    """Tasks already marked done should not appear in stale list."""
    item = _import_task(manager, "Done task", "ios-333")
    manager.complete_reminder(item.id)

    stale = manager.reverse_sync(active_ios_reminder_ids=set())
    assert stale == []


def test_emits_work_item_completed_events(manager):
    """Should emit WorkItemCompleted for each stale task resolved."""
    events = []
    manager.event_bus.subscribe(WorkItemCompleted, lambda e: events.append(e))

    item = _import_task(manager, "Event task", "ios-444")

    # Filter out any events from import
    events.clear()

    manager.reverse_sync(active_ios_reminder_ids=set())
    assert len(events) == 1
    assert events[0].work_item_id == item.id


def test_no_stale_when_all_ids_match(manager):
    """When all local reminder_ids are still active in iOS, nothing is stale."""
    item1 = _import_task(manager, "Active 1", "ios-555")
    item2 = _import_task(manager, "Active 2", "ios-666")

    stale = manager.reverse_sync(active_ios_reminder_ids={"ios-555", "ios-666"})
    assert stale == []


def test_skips_tasks_without_reminder_id(manager):
    """Tasks created manually (no reminder_id) should be ignored."""
    # Create via create_reminder (no reminder_id in registry)
    manual = manager.create_reminder(title="Manual task", priority="low")

    stale = manager.reverse_sync(active_ios_reminder_ids=set())
    assert manual.id not in stale
