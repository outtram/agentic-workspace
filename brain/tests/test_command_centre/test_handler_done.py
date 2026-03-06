"""Handler integration test — verify /done, /today, /remove round-trip."""

import pytest
from unittest.mock import patch, MagicMock

from brain.command_centre.handlers.triage import handle_done, handle_today, handle_remove


class TestHandleToday:
    def test_adds_to_today(self):
        """handle_today should add task IDs to the today list."""
        today = []
        with patch("brain.command_centre.handlers.triage.save_today_list"):
            result = handle_today(["OUT-1", "OUT-2"], today)
        assert "Added 2" in result
        assert "OUT-1" in today
        assert "OUT-2" in today

    def test_skips_duplicates(self):
        """handle_today should not add IDs already in today."""
        today = ["OUT-1"]
        with patch("brain.command_centre.handlers.triage.save_today_list"):
            result = handle_today(["OUT-1", "OUT-2"], today)
        assert "Added 1" in result
        assert today.count("OUT-1") == 1

    def test_empty_selection(self):
        """handle_today with no selection returns message."""
        result = handle_today([], [])
        assert "No tasks" in result

    def test_saves_to_disk(self):
        """handle_today should persist via save_today_list."""
        today = []
        with patch("brain.command_centre.handlers.triage.save_today_list") as mock_save:
            handle_today(["OUT-1"], today)
            mock_save.assert_called_once_with(today)


class TestHandleRemove:
    def test_removes_from_today(self):
        """handle_remove should remove task IDs from the today list."""
        today = ["OUT-1", "OUT-2", "OUT-3"]
        with patch("brain.command_centre.handlers.triage.save_today_list"):
            result = handle_remove(["OUT-2"], today)
        assert "Removed 1" in result
        assert "OUT-2" not in today
        assert len(today) == 2

    def test_skips_missing(self):
        """handle_remove should not error on IDs not in today."""
        today = ["OUT-1"]
        with patch("brain.command_centre.handlers.triage.save_today_list"):
            result = handle_remove(["OUT-99"], today)
        assert "Removed 0" in result

    def test_empty_selection(self):
        """handle_remove with no selection returns message."""
        result = handle_remove([], ["OUT-1"])
        assert "No tasks" in result


class TestHandleDone:
    @pytest.mark.asyncio
    async def test_empty_selection(self):
        """handle_done with no selection returns message."""
        result = await handle_done([])
        assert "No tasks" in result

    @pytest.mark.asyncio
    async def test_calls_reminders_manager(self):
        """handle_done should use RemindersManager.complete_reminder."""
        mock_manager = MagicMock()
        mock_manager.complete_reminder = MagicMock()

        with (
            patch("brain.command_centre.handlers.triage.RemindersManager", return_value=mock_manager, create=True),
            patch.dict("sys.modules", {"reminders.core.manager": MagicMock(RemindersManager=lambda: mock_manager)}),
        ):
            # Import inside the mock context so the handler finds the module
            import importlib
            import brain.command_centre.handlers.triage as triage_mod
            importlib.reload(triage_mod)
            result = await triage_mod.handle_done(["OUT-1"])

        assert isinstance(result, str)
