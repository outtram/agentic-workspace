"""E2E tests for Command Centre — Textual Pilot-based user flow tests.

Tests simulate real user interactions via keypresses and verify
widget state, data persistence, and modal behaviour.
"""

import pytest
from unittest.mock import patch, MagicMock

from brain.command_centre.app import CommandCentreApp, HelpOverlay
from brain.command_centre.tile_grid import TileGrid
from brain.command_centre.context_panel import ContextPanel
from brain.command_centre.command_palette import CommandPalette
from brain.command_centre.filter_picker import FilterPicker


# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

MOCK_TASKS = [
    {
        "id": "OUT-E2E-1",
        "title": "E2E task alpha",
        "status": "todo",
        "priority": "high",
        "eisenhower_quadrant": "q1",
        "_weight": 7,
        "_description": "First test task",
    },
    {
        "id": "OUT-E2E-2",
        "title": "E2E task beta",
        "status": "todo",
        "priority": "medium",
        "eisenhower_quadrant": "q2",
        "_weight": 5,
        "_description": "Second test task",
    },
    {
        "id": "OUT-E2E-3",
        "title": "E2E task gamma",
        "status": "todo",
        "priority": "low",
        "eisenhower_quadrant": "q3",
        "_weight": 3,
        "_description": "Third test task",
    },
    {
        "id": "OUT-E2E-4",
        "title": "E2E task delta",
        "status": "todo",
        "priority": "low",
        "eisenhower_quadrant": "q4",
        "_weight": 1,
        "_description": "Fourth test task",
    },
]


@pytest.fixture
def mock_env():
    """Patch external dependencies so E2E tests run in isolation."""
    with (
        patch("brain.command_centre.app.load_tasks", return_value=list(MOCK_TASKS)),
        patch("brain.command_centre.app.load_today_list", return_value=[]),
        patch("brain.command_centre.app.save_today_list") as mock_save_today,
        patch("brain.command_centre.app.generate_predictions", return_value=[]),
        patch("brain.command_centre.app.load_config", return_value={"hotkeys": {}}),
    ):
        yield {"save_today_list": mock_save_today}


# ---------------------------------------------------------------------------
# Today list — add task, verify persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_add_to_today_and_persist(mock_env):
    """Add focused task to today list, verify save_today_list is called."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Focus is on first tile (index 0) by default
        assert app.focus_index == 0

        # Press 't' to add focused task to today
        await pilot.press("t")

        # Task should be in today_ids
        assert "OUT-E2E-1" in app.today_ids

        # save_today_list should have been called (persistence)
        mock_env["save_today_list"].assert_called()
        saved_ids = mock_env["save_today_list"].call_args[0][0]
        assert "OUT-E2E-1" in saved_ids


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_toggle_today_removes_task(mock_env):
    """Pressing 't' twice should add then remove from today."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("t")
        assert "OUT-E2E-1" in app.today_ids

        # Press 't' again to remove
        await pilot.press("t")
        assert "OUT-E2E-1" not in app.today_ids


# ---------------------------------------------------------------------------
# Command palette — open, verify modal, dismiss
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_command_palette_opens_and_dismisses(mock_env):
    """'/' opens command palette, Escape closes it."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Open command palette
        await pilot.press("slash")
        assert len(app.screen_stack) > 1

        # Dismiss with Escape
        await pilot.press("escape")
        assert len(app.screen_stack) == 1


# ---------------------------------------------------------------------------
# Help system — opens, renders, dismisses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_help_overlay_renders_content(mock_env):
    """'?' opens help overlay with real content, any key closes it."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("question_mark")
        assert len(app.screen_stack) > 1

        # Help overlay should be on the stack
        top_screen = app.screen_stack[-1]
        assert isinstance(top_screen, HelpOverlay)

        # Pressing any key should dismiss
        await pilot.press("q")
        assert len(app.screen_stack) == 1


# ---------------------------------------------------------------------------
# Filter picker — open, dismiss
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_filter_picker_opens_and_dismisses(mock_env):
    """':' opens filter picker, Escape closes it."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("colon")
        assert len(app.screen_stack) > 1

        await pilot.press("escape")
        assert len(app.screen_stack) == 1


# ---------------------------------------------------------------------------
# Grid navigation — arrow keys, number jump, page
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_grid_navigation_arrows(mock_env):
    """Arrow keys move focus between tiles."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        assert app.focus_index == 0

        # Move right
        await pilot.press("right")
        assert app.focus_index == 1

        # Move right again
        await pilot.press("right")
        assert app.focus_index == 2

        # Move left
        await pilot.press("left")
        assert app.focus_index == 1

        # Move back to start
        await pilot.press("left")
        assert app.focus_index == 0

        # Down only works if row below has tasks (4 tasks = row 0 full, row 1 has 1)
        # From index 0, down goes to 3
        await pilot.press("down")
        assert app.focus_index == 3

        # Up goes back
        await pilot.press("up")
        assert app.focus_index == 0


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_grid_number_jump(mock_env):
    """Number keys 1-4 jump to corresponding tiles."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("3")
        assert app.focus_index == 2  # 0-indexed

        await pilot.press("1")
        assert app.focus_index == 0


# ---------------------------------------------------------------------------
# Selection — space toggles, 'a' selects all, 'n' deselects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_selection_toggle(mock_env):
    """Space toggles selection on focused tile."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        assert len(app.selected_ids) == 0

        await pilot.press("space")
        assert "OUT-E2E-1" in app.selected_ids

        await pilot.press("space")
        assert "OUT-E2E-1" not in app.selected_ids


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_select_all_and_deselect(mock_env):
    """'a' selects all visible tasks, 'n' deselects all."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("a")
        assert len(app.selected_ids) >= len(MOCK_TASKS)

        await pilot.press("n")
        assert len(app.selected_ids) == 0


# ---------------------------------------------------------------------------
# Focus view — drill down into leaf task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_drill_into_leaf_opens_focus_view(mock_env):
    """Enter on a leaf task opens focus view, Escape returns to grid."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        assert app._view_mode == "grid"

        # Press Enter on first task (leaf — no children)
        await pilot.press("enter")
        assert app._view_mode == "focus"

        # Escape should return to grid
        await pilot.press("escape")
        assert app._view_mode == "grid"


# ---------------------------------------------------------------------------
# Escape cascade — modal → filter → selection → quit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_escape_cascade_from_modal(mock_env):
    """Escape from modal returns to grid, not quit."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Open help
        await pilot.press("question_mark")
        assert len(app.screen_stack) > 1

        # Escape should close modal, not quit
        await pilot.press("escape")
        assert len(app.screen_stack) == 1
        assert app.is_running


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_escape_clears_selection_before_quit(mock_env):
    """Escape clears selection first, doesn't quit immediately."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Select a task
        await pilot.press("space")
        assert len(app.selected_ids) > 0

        # First Escape should clear selection
        await pilot.press("escape")
        assert len(app.selected_ids) == 0
        assert app.is_running


# ---------------------------------------------------------------------------
# Multi-select + add to today
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multi_select_add_to_today(mock_env):
    """Select multiple tasks, press 't' to add all to today."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Select first two tasks
        await pilot.press("space")  # Select task 1
        await pilot.press("right")
        await pilot.press("space")  # Select task 2

        assert "OUT-E2E-1" in app.selected_ids
        assert "OUT-E2E-2" in app.selected_ids

        # Add to today
        await pilot.press("t")

        # Both should be in today
        assert "OUT-E2E-1" in app.today_ids
        assert "OUT-E2E-2" in app.today_ids

        # Selection should be cleared after action
        assert len(app.selected_ids) == 0

        # Persistence
        mock_env["save_today_list"].assert_called()
