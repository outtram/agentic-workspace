"""TUI smoke test — verify app launches, renders tiles, and handles basic keys."""

import pytest
from unittest.mock import patch

from brain.command_centre.app import CommandCentreApp


MOCK_TASKS = [
    {
        "id": "OUT-SMOKE-1",
        "title": "Smoke test task one",
        "status": "open",
        "eisenhower_quadrant": "q1",
    },
    {
        "id": "OUT-SMOKE-2",
        "title": "Smoke test task two",
        "status": "open",
        "eisenhower_quadrant": "q2",
    },
]


@pytest.fixture
def mock_env():
    """Patch task loading so the app doesn't need real data files."""
    with (
        patch("brain.command_centre.app.load_tasks", return_value=MOCK_TASKS),
        patch("brain.command_centre.app.load_today_list", return_value=[]),
        patch("brain.command_centre.app.save_today_list"),
        patch("brain.command_centre.app.generate_predictions", return_value=[]),
        patch("brain.command_centre.app.load_config", return_value={"hotkeys": {}}),
    ):
        yield


@pytest.mark.asyncio
async def test_app_launches_and_renders(mock_env):
    """App should mount without crashing and render tile grid."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # App should be running
        assert app.is_running

        # Tile grid should exist
        from brain.command_centre.tile_grid import TileGrid
        grid = app.query_one("#tile-grid", TileGrid)
        assert grid is not None


@pytest.mark.asyncio
async def test_help_overlay_opens(mock_env):
    """Pressing ? should open the help overlay."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("question_mark")
        # Help overlay should be visible (pushed as modal)
        assert len(app.screen_stack) > 1


@pytest.mark.asyncio
async def test_command_palette_opens(mock_env):
    """Pressing / should open the command palette."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("slash")
        # Command palette modal should be on screen stack
        assert len(app.screen_stack) > 1


@pytest.mark.asyncio
async def test_filter_picker_opens(mock_env):
    """Pressing : should open the filter picker."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("colon")
        assert len(app.screen_stack) > 1


@pytest.mark.asyncio
async def test_escape_from_modal(mock_env):
    """Escape from a modal should close the modal, not quit."""
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("slash")
        assert len(app.screen_stack) > 1
        await pilot.press("escape")
        # Modal should be dismissed, back to main screen
        assert len(app.screen_stack) == 1
