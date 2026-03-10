"""Visual snapshot tests for Command Centre — SVG regression.

Uses pytest-textual-snapshot to capture SVG screenshots and diff
them between runs. Catches layout/styling regressions automatically.

First run generates baseline snapshots. Subsequent runs diff against them.
To update snapshots after intentional UI changes:
    pytest --snapshot-update brain/tests/test_command_centre/test_snapshots/
"""

import pytest
from unittest.mock import patch

from brain.command_centre.app import CommandCentreApp


# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

MOCK_TASKS = [
    {
        "id": "OUT-SNAP-1",
        "title": "Snapshot task alpha — high priority Q1",
        "status": "todo",
        "priority": "high",
        "eisenhower_quadrant": "q1",
        "_weight": 7,
        "_description": "Critical task for snapshot testing",
        "_overdue": True,
    },
    {
        "id": "OUT-SNAP-2",
        "title": "Snapshot task beta — Q2 scheduled",
        "status": "todo",
        "priority": "medium",
        "eisenhower_quadrant": "q2",
        "_weight": 5,
        "_description": "Medium priority scheduled task",
    },
    {
        "id": "OUT-SNAP-3",
        "title": "Snapshot task gamma — Q3 delegate",
        "status": "todo",
        "priority": "low",
        "eisenhower_quadrant": "q3",
        "_weight": 3,
        "_description": "Low priority delegatable task",
    },
    {
        "id": "OUT-SNAP-4",
        "title": "Snapshot task delta — Q4 eliminate",
        "status": "todo",
        "priority": "low",
        "eisenhower_quadrant": "q4",
        "_weight": 1,
        "_description": "Lowest priority task",
    },
    {
        "id": "OUT-SNAP-5",
        "title": "Snapshot task epsilon — another Q1",
        "status": "todo",
        "priority": "high",
        "eisenhower_quadrant": "q1",
        "_weight": 6,
        "_description": "Another critical task",
    },
    {
        "id": "OUT-SNAP-6",
        "title": "Snapshot task zeta — Q2 item",
        "status": "todo",
        "priority": "medium",
        "eisenhower_quadrant": "q2",
        "_weight": 4,
        "_description": "Scheduled Q2 task",
    },
]


@pytest.fixture
def mock_env():
    """Patch external dependencies for isolated visual tests."""
    with (
        patch("brain.command_centre.app.load_tasks", return_value=list(MOCK_TASKS)),
        patch("brain.command_centre.app.load_today_list", return_value=[]),
        patch("brain.command_centre.app.save_today_list"),
        patch("brain.command_centre.app.generate_predictions", return_value=[]),
        patch("brain.command_centre.app.load_config", return_value={"hotkeys": {}}),
    ):
        yield


# Note: snap_compare runs its own event loop, so these must be sync functions.


@pytest.mark.snapshot
def test_main_grid_layout(mock_env, snap_compare):
    """Baseline snapshot of the main 3x3 tile grid."""
    assert snap_compare(
        CommandCentreApp(),
        terminal_size=(120, 40),
    )


@pytest.mark.snapshot
def test_help_overlay_layout(mock_env, snap_compare):
    """Snapshot of help overlay content and positioning."""
    assert snap_compare(
        CommandCentreApp(),
        press=["question_mark"],
        terminal_size=(120, 40),
    )


@pytest.mark.snapshot
def test_command_palette_layout(mock_env, snap_compare):
    """Snapshot of command palette modal."""
    assert snap_compare(
        CommandCentreApp(),
        press=["slash"],
        terminal_size=(120, 40),
    )


@pytest.mark.snapshot
def test_filter_picker_layout(mock_env, snap_compare):
    """Snapshot of filter picker modal."""
    assert snap_compare(
        CommandCentreApp(),
        press=["colon"],
        terminal_size=(120, 40),
    )


@pytest.mark.snapshot
def test_focus_view_layout(mock_env, snap_compare):
    """Snapshot of focus view when entering a leaf task."""
    assert snap_compare(
        CommandCentreApp(),
        press=["enter"],
        terminal_size=(120, 40),
    )


@pytest.mark.snapshot
def test_small_terminal_layout(mock_env, snap_compare):
    """Snapshot at a small terminal size (80x24)."""
    assert snap_compare(
        CommandCentreApp(),
        terminal_size=(80, 24),
    )


@pytest.mark.snapshot
def test_wide_terminal_layout(mock_env, snap_compare):
    """Snapshot at a wide terminal size (200x50)."""
    assert snap_compare(
        CommandCentreApp(),
        terminal_size=(200, 50),
    )


@pytest.mark.snapshot
def test_selected_tile_styling(mock_env, snap_compare):
    """Snapshot showing selected tile border styling."""
    assert snap_compare(
        CommandCentreApp(),
        press=["space"],
        terminal_size=(120, 40),
    )
