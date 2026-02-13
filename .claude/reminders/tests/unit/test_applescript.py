import pytest
from reminders.adapters.applescript import AppleScriptAdapter
from reminders.tests.fixtures.mock_applescript import MockAppleScriptAdapter


def test_create_reminder():
    """Should create reminder via AppleScript"""
    adapter = MockAppleScriptAdapter()

    reminder_id = adapter.create_reminder(
        name="Call Leon",
        body="Discuss equity partner",
        tags=["phone", "urgent"],
        due_date="2026-02-14",
        priority=1,
        list_name="Reminders"
    )

    assert reminder_id.startswith("mock-reminder-")
    assert len(adapter.call_log) == 1
    assert adapter.call_log[0] == ("create", "Call Leon", "Reminders")

    # Verify reminder stored
    reminder = adapter.get_reminder(reminder_id)
    assert reminder["name"] == "Call Leon"
    assert "phone" in reminder["tags"]


def test_fetch_all_reminders():
    """Should fetch all active reminders"""
    adapter = MockAppleScriptAdapter()

    adapter.create_reminder("Task 1")
    adapter.create_reminder("Task 2")

    reminders = adapter.fetch_all_reminders()
    assert len(reminders) == 2


def test_update_reminder():
    """Should update reminder fields"""
    adapter = MockAppleScriptAdapter()

    reminder_id = adapter.create_reminder("Original name")
    adapter.update_reminder(reminder_id, name="Updated name")

    reminder = adapter.get_reminder(reminder_id)
    assert reminder["name"] == "Updated name"


def test_delete_reminder():
    """Should delete reminder from store"""
    adapter = MockAppleScriptAdapter()

    reminder_id = adapter.create_reminder("To delete")
    adapter.delete_reminder(reminder_id)

    assert adapter.get_reminder(reminder_id) is None


def test_delete_nonexistent_raises():
    """Should raise ValueError for nonexistent reminder"""
    adapter = MockAppleScriptAdapter()

    with pytest.raises(ValueError):
        adapter.delete_reminder("nonexistent-id")


def test_fetch_excludes_completed():
    """Should not return completed reminders"""
    adapter = MockAppleScriptAdapter()

    rid1 = adapter.create_reminder("Active task")
    rid2 = adapter.create_reminder("Completed task")
    adapter.update_reminder(rid2, completed=True)

    reminders = adapter.fetch_all_reminders()
    assert len(reminders) == 1
    assert reminders[0]["name"] == "Active task"
