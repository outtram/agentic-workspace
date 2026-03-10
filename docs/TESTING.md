# Testing Strategy — Command Centre

## Overview

CC testing uses three layers, each catching different classes of bugs:

| Layer | Tool | Speed | What it catches |
|---|---|---|---|
| **Unit tests** | pytest | Fast | Logic errors in individual modules |
| **E2E Pilot tests** | Textual `run_test()` + Pilot | Medium | Broken user flows, state management bugs, data persistence |
| **Visual snapshots** | pytest-textual-snapshot | Medium | Layout regressions, styling breaks, responsive issues |

## Running Tests

```bash
# All CC tests
python3 -m pytest brain/tests/test_command_centre/ -x -q

# Only E2E flow tests
python3 -m pytest brain/tests/test_command_centre/test_e2e/ -x -q

# Only visual snapshot tests
python3 -m pytest brain/tests/test_command_centre/test_snapshots/ -x -q

# By marker
python3 -m pytest -m e2e -x -q
python3 -m pytest -m snapshot -x -q
```

## Visual Snapshot Tests

Snapshots are SVG files stored alongside tests. On first run, baselines are generated automatically.

### Updating snapshots after intentional UI changes

```bash
python3 -m pytest --update-snapshots brain/tests/test_command_centre/test_snapshots/
```

Review the diff to confirm changes are intentional, then commit the updated snapshot files.

### How it works

1. `snap_compare()` launches the app headless at a given terminal size
2. Optionally sends keypresses (e.g. `press=["slash"]` to open command palette)
3. Captures an SVG screenshot
4. Compares against the stored baseline
5. Fails if they differ (with an HTML diff report)

## E2E Pilot Tests

Pilot tests simulate real user flows:

```python
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_add_to_today(mock_env):
    app = CommandCentreApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("t")
        assert "OUT-E2E-1" in app.today_ids
```

### What Pilot can do

- `pilot.press("key")` — simulate keypresses (arrows, enter, escape, letters)
- `pilot.click("#widget-id")` — click a widget by CSS selector
- `app.query_one("#id", WidgetType)` — query widget state
- `app.screen_stack` — check modal state
- `app.is_running` — verify app hasn't crashed

### Mock fixture

All E2E tests use a `mock_env` fixture that patches external dependencies:
- `load_tasks` — returns deterministic mock data
- `load_today_list` / `save_today_list` — isolated from real files
- `generate_predictions` — returns empty (no API calls)
- `load_config` — default hotkeys

## Test Markers

| Marker | Description |
|---|---|
| `@pytest.mark.tui` | Widget-level TUI tests |
| `@pytest.mark.handler` | Handler integration tests |
| `@pytest.mark.e2e` | End-to-end Pilot flow tests |
| `@pytest.mark.snapshot` | Visual regression snapshots |
| `@pytest.mark.slow` | Tests taking >5s |

## Writing New Tests

When building a new CC feature:

1. Write Pilot E2E test covering the user flow
2. Add a visual snapshot if the feature changes layout
3. Run the full suite before committing

```bash
python3 -m pytest brain/tests/test_command_centre/ -x -q
```

## Why Not agent-browser?

agent-browser (Vercel) drives Chromium via the DOM accessibility tree. It cannot interact with terminal/TUI apps. CC is a Textual TUI, so we use Textual's native testing tools instead.

agent-browser is still useful for testing web-based outputs (Eisenhower dashboard HTML, architecture viewer).
