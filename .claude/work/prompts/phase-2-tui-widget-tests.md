# Phase 2: TUI Widget Tests

> Prompt for Claude Code — implements widget-level tests for Command Centre

## Context

The Command Centre (`brain/command_centre/`) is a Textual TUI with these widgets:
- **TileGrid** — 3×3 task tile grid with focus/select/pagination
- **TaskFocusView** — single-task detail view with field-by-field editing
- **ContextPanel** — right-side panel (info mode + chat mode)
- **DiagramGrid** — dynamic diagram node grid with drill-down layers
- **FilterPicker** — modal for selecting quadrant/status filters
- **CommandPalette** — modal for commands/agents/skills

Phase 1 (done) fixed broken tests and added smoke tests. Phase 2 adds widget-level tests that verify rendering, state transitions, and user interactions.

## Pre-existing Test Patterns

Use the same mock fixtures from `brain/tests/test_command_centre/test_tui_smoke.py`:

```python
from unittest.mock import patch

MOCK_TASKS = [
    {"id": "OUT-T1", "title": "Task one", "status": "open", "eisenhower_quadrant": "q1"},
    {"id": "OUT-T2", "title": "Task two", "status": "open", "eisenhower_quadrant": "q2"},
    # ... etc
]

@pytest.fixture
def mock_env():
    with (
        patch("brain.command_centre.app.load_tasks", return_value=MOCK_TASKS),
        patch("brain.command_centre.app.load_today_list", return_value=[]),
        patch("brain.command_centre.app.save_today_list"),
        patch("brain.command_centre.app.generate_predictions", return_value=[]),
        patch("brain.command_centre.app.load_config", return_value={"hotkeys": {}}),
    ):
        yield
```

For widget-only tests (no app mount), instantiate widgets directly and call methods.

## Tests to Write

### File 1: `brain/tests/test_command_centre/test_tile_grid.py`

Test the TileGrid widget's rendering logic.

**Test class: TestTileRendering**
1. `test_renders_9_tiles` — call `update_tiles()` with 9 tasks, verify all 9 tile Statics have content
2. `test_empty_tiles_when_few_tasks` — pass 3 tasks, verify tiles 4-9 show empty state
3. `test_focused_tile_has_class` — verify the tile at `focus_index` gets the `focused` CSS class
4. `test_selected_tile_has_class` — pass a task ID in `selected_ids`, verify that tile gets `selected` class
5. `test_today_badge_shown` — pass a task ID in `today_ids`, verify the rendered markup contains a today indicator

**Test class: TestTileNavigation** (requires app mount with `run_test`)
6. `test_arrow_right_moves_focus` — press right arrow, verify `app.focus_index` increments
7. `test_arrow_down_moves_focus` — press down arrow, verify focus moves by 3 (row width)
8. `test_focus_wraps_at_page_boundary` — arrow right at tile 9 should not go past last tile
9. `test_number_key_jumps` — press `5`, verify focus jumps to tile index 4 (0-based)
10. `test_space_toggles_select` — press space on focused tile, verify its ID appears in `app.selected_ids`; press again, verify removed

**Test class: TestPagination**
11. `test_bracket_right_pages_forward` — with 12+ tasks, press `]`, verify `app.current_page` increments
12. `test_bracket_left_pages_backward` — page forward then `[`, verify page decrements
13. `test_page_0_no_backward` — on page 0, press `[`, verify stays on page 0

### File 2: `brain/tests/test_command_centre/test_task_focus.py`

Test the TaskFocusView field navigation and editing.

**Test class: TestFocusViewFields** (requires app mount)
14. `test_enter_on_leaf_opens_focus` — with mock tasks (no children), press Enter, verify `app._view_mode == "focus"`
15. `test_escape_returns_to_grid` — enter focus view, press Escape, verify `app._view_mode == "grid"`
16. `test_field_cursor_moves` — in focus view, press down arrow, verify cursor moves to next field
17. `test_quadrant_cycles_on_enter` — focus on quadrant field, press Enter repeatedly, verify cycles q1→q2→q3→q4→q1

**Test class: TestFocusViewEditing**
18. `test_title_edit_commits` — focus title field, press Enter, type new text, press Enter, verify task title updated
19. `test_escape_cancels_edit` — start editing, press Escape, verify original value preserved
20. `test_note_hotkey_adds_note` — press `n` in focus view, verify note input appears

### File 3: `brain/tests/test_command_centre/test_context_panel.py`

Test the ContextPanel's dual-mode behaviour.

**Test class: TestContextPanelModes**
21. `test_default_mode_is_info` — verify panel starts in info mode
22. `test_toggle_switches_to_chat` — press `c`, verify panel switches to chat mode
23. `test_toggle_back_to_info` — press `c` twice, verify back to info mode

**Test class: TestContextPanelContent**
24. `test_today_list_renders` — set `today_ids` with known tasks, verify panel shows their titles
25. `test_focused_task_detail_shows` — focus a task, verify panel shows its quadrant and description

### File 4: `brain/tests/test_command_centre/test_filter_picker_widget.py`

Test the FilterPicker modal behaviour.

**Test class: TestFilterPicker**
26. `test_shows_all_filters` — mount FilterPicker, verify all 7 default filters render
27. `test_typing_filters_list` — type "over" in the input, verify only "overdue" filter visible
28. `test_enter_selects_filter` — arrow down to q2, press Enter, verify dismissed with "q2"
29. `test_escape_dismisses_none` — press Escape, verify dismissed with None
30. `test_freetext_passthrough` — type "bananas" (no match), press Enter, verify dismissed with "bananas" as search term

### File 5: `brain/tests/test_command_centre/test_command_palette_widget.py`

Test the CommandPalette modal behaviour.

**Test class: TestCommandPalette**
31. `test_shows_commands_agents_skills` — mount palette, verify items from all 3 categories render
32. `test_typing_filters_items` — type "done", verify only matching items visible
33. `test_enter_selects_command` — select `/today`, verify dismissed with "/today"
34. `test_contextual_suggestions` — pass a task dict, verify "suggested" category appears first

## Guidelines

- Mark all TUI tests with `@pytest.mark.tui`
- Use `app.run_test(size=(120, 40))` for all mounted tests
- Always use `mock_env` fixture when mounting CommandCentreApp
- For widget-only tests that don't need the full app, test pure logic methods directly
- Don't test Rich markup strings exactly — use `in` checks for key content
- Each test file should be self-contained with its own imports and fixtures
- Use the pattern: arrange → act → assert (one assertion per test where practical)
- Verify with: `python3 -m pytest brain/tests/test_command_centre/ -x -q`
- All tests must pass alongside existing tests (282 currently passing)

## Verification

```bash
# Syntax check all new files
python3 -m py_compile brain/tests/test_command_centre/test_tile_grid.py
python3 -m py_compile brain/tests/test_command_centre/test_task_focus.py
python3 -m py_compile brain/tests/test_command_centre/test_context_panel.py
python3 -m py_compile brain/tests/test_command_centre/test_filter_picker_widget.py
python3 -m py_compile brain/tests/test_command_centre/test_command_palette_widget.py

# Run new tests
python3 -m pytest brain/tests/test_command_centre/ -x -q

# Run full suite
python3 -m pytest brain/tests/ -q
```

Expected: 34 new tests + 282 existing = 316+ total, all passing.
