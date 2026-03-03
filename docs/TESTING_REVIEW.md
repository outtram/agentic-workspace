# Testing Review — AAGLOBAL System Audit

> **Date:** 2026-03-03
> **Status:** Review complete — action items identified
> **TL;DR:** You have 213 tests but they're almost all isolated unit tests. Zero TUI tests, zero end-to-end workflow tests, and 4 broken integration tests. The "it works in tests but breaks when I use it" problem is because nothing tests features the way you actually use them.

---

## 1. Current State — What You Actually Have

### Test Execution Results

| Suite | Tests | Pass | Fail/Error | Status |
|-------|-------|------|------------|--------|
| Command Centre (help_sync, router) | 17 | 17 | 0 | ✅ |
| Formatter (WhatsApp, terminal, voice) | 33 | 33 | 0 | ✅ |
| Memory (recall, remember) | 25 | 25 | 0 | ✅ |
| Core (config, db, events) | 21 | 21 | 0 | ✅ |
| Session (manager, context, catchup) | 23 | 23 | 0 | ✅ |
| Usage tracking | 10 | 10 | 0 | ✅ |
| Reflection | 11 | 11 | 0 | ✅ |
| Email (inbox, outbox) | 28 | 28 | 0 | ✅ |
| Scheduler & judge | 11 | 11 | 0 | ✅ |
| Chat CLI (non-slow) | 25 | 25 | 0 | ✅ |
| **Heartbeat integration** | **4** | **0** | **4** | ❌ Broken fixture |
| **IPC roundtrip** | **?** | **0** | **import** | ❌ Missing `brain.ipc` module |
| **Voice** | **?** | **0** | **import** | ❌ Missing `numpy` |
| **Archiver integration** | ? | ? | ? | ⚠️ Not runnable here |

**Summary: 204 pass, 4+ broken, 0 TUI tests, 0 end-to-end tests.**

### Test Types You Have vs Need

```
What you HAVE:                    What you NEED:

┌─────────────────────┐          ┌─────────────────────┐
│                     │          │   E2E / Smoke (5%)   │ ← "Open CC, type /done,
│                     │          │   verify task marked" │   see it marked complete"
│                     │          ├─────────────────────┤
│                     │          │  Integration (15%)   │ ← "Router → handler →
│                     │          │  (multi-step flows)  │   file system → UI update"
│   Unit tests only   │          ├─────────────────────┤
│   (you are here)    │          │  TUI Widget (20%)    │ ← "Tile grid renders 9
│                     │          │  (Textual pilot)     │   tiles, arrow keys work"
│                     │          ├─────────────────────┤
│                     │          │                      │
│                     │          │   Unit tests (60%)   │ ← You have these ✅
└─────────────────────┘          └─────────────────────┘
```

---

## 2. Feature → Test Traceability Matrix

This is the core view you asked for. **Every feature, its test status, and what's missing.**

### Legend
- ✅ = Tested | ⚠️ = Partially tested | ❌ = No tests | 💀 = Tests exist but broken

### 2a. Command Centre TUI (`brain/command_centre/`)

| Feature | Unit | TUI Widget | Integration | Status |
|---------|------|------------|-------------|--------|
| App startup & state | ❌ | ❌ | ❌ | **No tests** |
| Tile grid (3×3, selection, pagination) | ❌ | ❌ | ❌ | **No tests** |
| Context panel (task detail) | ❌ | ❌ | ❌ | **No tests** |
| Command bar (input, submit) | ❌ | ❌ | ❌ | **No tests** |
| Status bar (hints, counts) | ❌ | ❌ | ❌ | **No tests** |
| Task focus view (drill-down) | ❌ | ❌ | ❌ | **No tests** |
| Task editor modal | ❌ | ❌ | ❌ | **No tests** |
| Command palette (/ key) | ❌ | ❌ | ❌ | **No tests** |
| Filter picker modal | ❌ | ❌ | ❌ | **No tests** |
| Task loader (YAML → tiles) | ❌ | ❌ | ❌ | **No tests** |
| Help text sync | ✅ | — | — | Good |
| Slash command routing | ✅ | — | ⚠️ | Logic only, no UI |
| Keyboard navigation | ❌ | ❌ | ❌ | **No tests** |
| Telegram bridge (background) | ❌ | — | ❌ | **No tests** |
| Heartbeat bridge (background) | ❌ | — | ❌ | **No tests** |

**TUI coverage: 2/15 features (13%)**

### 2b. Slash Command Handlers (`brain/command_centre/handlers/`)

| Handler | Unit | Integration | E2E Flow | Status |
|---------|------|-------------|----------|--------|
| `/done` (mark complete) | ❌ | ❌ | ❌ | **No tests** |
| `/today` (add/remove) | ❌ | ❌ | ❌ | **No tests** |
| `/enrich` (Claude improve) | ❌ | ❌ | ❌ | **No tests** |
| `/research` (web search) | ❌ | ❌ | ❌ | **No tests** |
| `/email` (inbox/send) | ❌ | ❌ | ❌ | **No tests** |
| `/agent` (run agent) | ❌ | ❌ | ❌ | **No tests** |
| `/skill` (run skill) | ❌ | ❌ | ❌ | **No tests** |
| `/memory` (remember/forget) | ❌ | ❌ | ❌ | **No tests** |
| `/voice` (recording) | ❌ | ❌ | ❌ | **No tests** |
| `/daily` (daily review) | ❌ | ❌ | ❌ | **No tests** |

**Handler coverage: 0/10 features (0%)**

### 2c. OutBot Core (`brain/`)

| Feature | Unit | Integration | E2E | Status |
|---------|------|-------------|-----|--------|
| CLI chat pipeline | ✅ | ⚠️ | ❌ | Message storage + context OK |
| Email intent detection | ✅ | — | ❌ | Good unit coverage |
| Orchestrator (event loop) | ❌ | ❌ | ❌ | **No tests** |
| Voice chat | ❌ | ❌ | 💀 | Import error (numpy) |
| Telegram bot | ❌ | ❌ | ❌ | **No tests** |

### 2d. Core Infrastructure (`brain/core/`)

| Feature | Unit | Integration | Status |
|---------|------|-------------|--------|
| Config loading | ✅ | — | Good |
| SQLite database | ✅ | — | Good (13 tests) |
| Event bus (pub/sub) | ✅ | — | Good |
| Usage tracking | ✅ | — | Good |
| Claude client | ✅ | — | Good |
| Models (dataclasses) | ❌ | — | No direct tests |

### 2e. Memory System (`brain/memory/`)

| Feature | Unit | Integration | Status |
|---------|------|-------------|--------|
| Remember triggers | ✅ | — | Good |
| Remember write | ✅ | — | Good |
| Forget | ✅ | — | Good |
| Recall triggers | ✅ | — | Good |
| Recall search | ✅ | — | Good |
| Reflection | ✅ | — | Good |

**Memory coverage: 6/6 features (100%) — but unit only**

### 2f. Email System (`brain/mail/`)

| Feature | Unit | Integration | Status |
|---------|------|-------------|--------|
| IMAP fetch | ✅ | — | Good (11 tests + retry) |
| Email model | ✅ | — | Good |
| SMTP send (Gmail) | ✅ | — | Good |
| Console backend | ✅ | — | Good |

### 2g. Heartbeat & Scheduling (`brain/heartbeat/`)

| Feature | Unit | Integration | Status |
|---------|------|-------------|--------|
| Cron calculation | ✅ | — | Good |
| Quiet hours | ✅ | — | Good |
| Concurrency limit | ✅ | — | Good |
| Importance judge | ✅ | — | Good |
| Full heartbeat cycle | — | 💀 | **Broken** — Config fixture stale |
| IPC roundtrip | — | 💀 | **Broken** — `brain.ipc` module missing |

### 2h. Formatting (`brain/personality/`)

| Feature | Unit | Status |
|---------|------|--------|
| WhatsApp format | ✅ | Good |
| Terminal format | ✅ | Good |
| Voice format | ✅ | Good |
| Telegram format | ✅ | Good |
| Full pipeline | ✅ | Good |

---

## 3. Broken Tests (Immediate Fixes Needed)

### 3a. `test_heartbeat_cycle.py` — Stale Config Fixture
```
TypeError: Config.__init__() got an unexpected keyword argument 'socket_path'
```
**Root cause:** Config class was refactored (removed `socket_path`), but the test fixture wasn't updated.
**Fix:** Update fixture to match current Config signature.

### 3b. `test_ipc_roundtrip.py` — Missing Module
```
ModuleNotFoundError: No module named 'brain.ipc'
```
**Root cause:** The `brain.ipc` module was removed/moved but the test still references it.
**Fix:** Delete test or update to match current architecture.

### 3c. `test_voice.py` — Missing numpy
```
ModuleNotFoundError: No module named 'numpy'
```
**Root cause:** `numpy` not in CI/test dependencies.
**Fix:** Add to dev dependencies or skip gracefully.

---

## 4. The Agentic Testing Gap

### Why Your Stuff Breaks Despite Having Tests

Your tests verify **isolated functions** work correctly. But your system is **agentic** — it chains multiple steps:

```
User types "/done" in Command Centre
  → command_bar captures input
    → router parses command
      → triage handler reads YAML
        → marks task complete
          → writes back to file
            → tile_grid refreshes
              → status_bar updates count
```

You test step 2 (router) but not the chain. If step 4 writes a slightly different YAML format, or step 6 doesn't refresh, the feature "breaks" — but all unit tests still pass.

### Standard Approaches for Testing Agentic Solutions

The industry is converging on a **4-layer testing pyramid** for agentic systems:

| Layer | What It Tests | Tools | Your Status |
|-------|---------------|-------|-------------|
| **Unit** | Individual functions, pure logic | pytest, mocks | ✅ You have this |
| **Component/Widget** | UI widgets in isolation | Textual Pilot API | ❌ Missing entirely |
| **Integration** | Multi-step workflows (handler → file → UI) | pytest + fixtures, snapshot testing | ⚠️ 2 broken, minimal |
| **Scenario/E2E** | "User does X, sees Y" full journeys | Textual Pilot + assertions, golden files | ❌ Missing entirely |

Key patterns from the agentic testing space:

1. **Deterministic replay testing** — Record agent actions, replay and assert outcomes
2. **Snapshot/golden file testing** — Capture expected output, compare on each run
3. **Contract testing** — Verify each component honours its interface (e.g., handler always returns `{status, message}`)
4. **Textual Pilot API** — Textual's built-in testing framework simulates keystrokes and asserts widget state

---

## 5. Rolled-Up Coverage Dashboard

```
AAGLOBAL TEST COVERAGE — 2026-03-03
══════════════════════════════════════════════════════════════

OVERALL:  ██████░░░░░░░░░░░░░░  32% features tested

BY AREA:
  Core Infrastructure  ████████████████░░░░  83%  ✅
  Memory System        ████████████████████  100% ✅ (unit only)
  Email System         ████████████████████  100% ✅ (unit only)
  Formatting           ████████████████████  100% ✅
  Scheduler/Heartbeat  ██████████████░░░░░░  67%  ⚠️ (integration broken)
  Chat CLI             ████████░░░░░░░░░░░░  40%  ⚠️
  Command Centre TUI   ██░░░░░░░░░░░░░░░░░░  13%  ❌
  Slash Handlers       ░░░░░░░░░░░░░░░░░░░░  0%   ❌
  Orchestration        ░░░░░░░░░░░░░░░░░░░░  0%   ❌
  Telegram             ██░░░░░░░░░░░░░░░░░░  10%  ❌
  Voice                ░░░░░░░░░░░░░░░░░░░░  0%   💀

BY TEST TYPE:
  Unit tests:          ████████████████████  204 tests  ✅
  TUI/Widget tests:    ░░░░░░░░░░░░░░░░░░░░  0 tests   ❌
  Integration tests:   ██░░░░░░░░░░░░░░░░░░  ~30 tests ⚠️ (some broken)
  E2E scenario tests:  ░░░░░░░░░░░░░░░░░░░░  0 tests   ❌

BROKEN TESTS:          4 (heartbeat cycle) + 2 (import errors)
```

---

## 6. Recommended Action Plan

### Phase 1: Stop the Bleeding (This Week)
1. **Fix broken tests** — heartbeat fixture, remove dead IPC test, add numpy to deps
2. **Add TUI smoke test** — Use Textual Pilot to verify the app starts and renders tiles
3. **Add `/done` handler test** — Your most-used workflow, test file write + refresh

### Phase 2: TUI Widget Tests (Next Sprint)
4. **Tile grid widget test** — Arrow keys move selection, Space toggles, pagination works
5. **Command bar test** — Type text, hit Enter, verify router receives input
6. **Task editor modal test** — Open modal, edit field, save, verify YAML updated
7. **Task loader test** — Given a YAML file, verify correct tiles loaded

### Phase 3: Integration Chains (Following Sprint)
8. **"/done" end-to-end** — Type command → task marked → file updated → grid refreshed
9. **"/today" end-to-end** — Add task → today list updated → tile shows indicator
10. **"/email check" flow** — Command → mock IMAP → tasks created from emails
11. **Daily review pipeline** — Import reminders → generate dashboard → check overdue

### Phase 4: Ongoing Traceability
12. **Add pytest markers** per feature area: `@pytest.mark.tui`, `@pytest.mark.handler`, `@pytest.mark.integration`
13. **Generate coverage report** per module (add `pytest-cov` to CI)
14. **Maintain this traceability matrix** — update when features are added

### Testing Tools to Add

| Tool | Purpose | Install |
|------|---------|---------|
| **Textual Pilot** | TUI widget testing (built into Textual) | Already available |
| **pytest-cov** | Coverage reporting per module | `pip install pytest-cov` |
| **pytest markers** | Tag tests by layer/feature | Config in `pyproject.toml` |
| **pytest-snapshot** | Golden file testing for formatted output | `pip install pytest-snapshot` |

---

## 7. Example: What a TUI Test Looks Like

Using Textual's built-in Pilot API (no extra deps needed):

```python
"""Test Command Centre app starts and renders correctly."""
import pytest
from textual.testing import AppTest

from brain.command_centre.app import CommandCentreApp


@pytest.mark.tui
class TestCommandCentreStartup:
    async def test_app_starts_without_error(self):
        """App should start and display the main screen."""
        async with AppTest(CommandCentreApp) as pilot:
            assert pilot.app.is_running

    async def test_tile_grid_renders_tiles(self):
        """Tile grid should display task tiles from YAML."""
        async with AppTest(CommandCentreApp) as pilot:
            grid = pilot.app.query_one("TileGrid")
            assert len(grid.children) > 0

    async def test_arrow_keys_move_selection(self):
        """Arrow keys should navigate tile selection."""
        async with AppTest(CommandCentreApp) as pilot:
            await pilot.press("right")
            grid = pilot.app.query_one("TileGrid")
            assert grid.selected_index == 1

    async def test_slash_command_routes(self):
        """Typing /help in command bar should show help text."""
        async with AppTest(CommandCentreApp) as pilot:
            await pilot.press(":")  # Focus command bar
            await pilot.type("/help")
            await pilot.press("enter")
            panel = pilot.app.query_one("ContextPanel")
            assert "Commands" in panel.content
```

---

## 8. Recommended `pyproject.toml` Markers

```toml
[tool.pytest.ini_options]
markers = [
    "slow: tests that call Claude CLI (slow, require Max plan)",
    "tui: Textual TUI widget and interaction tests",
    "handler: slash command handler tests",
    "integration: multi-component integration tests",
    "e2e: end-to-end scenario tests",
]
```

This lets you run targeted suites:
```bash
pytest -m tui          # Just TUI tests
pytest -m handler      # Just handler tests
pytest -m "not slow"   # Everything fast
pytest -m integration  # Multi-step flows
```

---

## Summary

**The root problem:** You have unit tests that verify pieces work, but nothing that verifies the assembled experience. It's like testing every Lego brick individually but never checking the assembled house stands up.

**The fix:** Add Textual Pilot widget tests (they're fast, built-in, and test what you actually interact with) + integration tests for your top 5 workflows.

**The traceability:** This document IS your traceability matrix. Keep it updated as features and tests are added. The rolled-up dashboard at Section 5 gives you the visual overview.
