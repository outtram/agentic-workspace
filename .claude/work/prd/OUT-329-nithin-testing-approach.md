---
id: OUT-329
title: CC E2E regression testing with Textual Pilot + visual snapshots
type: prd
status: draft
priority: q2
created: 2026-03-09
updated: 2026-03-09
assignee: Troy
branch: feature/OUT-329-nithin-testing-approach
---

# CC End-to-End Regression Testing

## Problem

The Command Centre (CC) has minimal E2E regression coverage (2 smoke tests). UI refactors can break flows without detection. We need a testing layer that:
- Tests real user-facing behaviour (not implementation details)
- Catches visual regressions automatically
- Can be written by AI agents during development, not retrofitted after

Original inspiration: https://dev.to/hybridtechie/ai-regression-tests-written-in-markdown-not-code-5b09

## Research Findings — Why Not agent-browser

**agent-browser is browser-only.** It drives Chromium via the DOM accessibility tree — it cannot interact with terminal/TUI apps. CC is a Textual TUI, so agent-browser is the wrong tool here.

**What works for Textual TUIs:**
- **Textual Pilot** (`App.run_test()` + `pilot`) — already working in `test_tui_smoke.py`. Simulates keypresses, clicks, queries widget state. Fast, Python-native, no real terminal needed.
- **pytest-textual-snapshot** — SVG visual regression. Captures screenshots, diffs between runs, produces HTML diff reports. Catches layout/styling breaks automatically.
- **Microsoft tui-test** — True PTY-based E2E (Playwright-for-terminals). TypeScript, pre-release (v0.0.1-rc.5). Not recommended yet.

**agent-browser stays useful** for testing web-based outputs (Eisenhower dashboard HTML, architecture viewer).

## Solution

Extend the existing Textual Pilot test suite with comprehensive E2E coverage, and add pytest-textual-snapshot for visual regression.

**Two layers:**
1. **Pilot E2E tests** — simulate user flows, assert widget state and data persistence
2. **Visual snapshot tests** — SVG regression catches layout/styling breaks without manual inspection

## Requirements

### Infrastructure
- [ ] Install `pytest-textual-snapshot` (`pip install pytest-textual-snapshot`)
- [ ] Create `brain/tests/test_command_centre/test_e2e/` for E2E Pilot tests
- [ ] Create `brain/tests/test_command_centre/test_snapshots/` for visual regression
- [ ] Add pytest markers: `@pytest.mark.e2e`, `@pytest.mark.snapshot`
- [ ] Document test strategy in `docs/TESTING.md`

### Critical CC E2E Tests (Pilot)
- [ ] **Today list** — add task, mark done, verify persistence (covers data-loss bug)
- [ ] **Reminders sync** — trigger sync, verify tasks appear in today list
- [ ] **Command palette** — open with `/`, search for a command, execute it
- [ ] **Help system** — trigger `?`, verify help overlay renders correctly
- [ ] **Email import** — `/import-emails` flow completes without crash
- [ ] **Eisenhower dashboard** — tasks appear in correct quadrants
- [ ] **Session save/restore** — quit CC, reopen, verify state persists

### Visual Snapshot Tests
- [ ] **Main grid layout** — tile grid renders at standard terminal sizes
- [ ] **Help overlay** — help screen layout and content
- [ ] **Context panel** — detail view when a tile is selected
- [ ] **Command palette** — palette appearance and search results
- [ ] **Responsive layout** — grid adapts at small/medium/large terminal sizes

### Test Authoring Convention
- [ ] Tests written alongside features (not retrofitted)
- [ ] Pilot tests use descriptive function names: `test_today_list_add_and_complete_task`
- [ ] Visual snapshots auto-generated, reviewed on first run, diffed on subsequent runs
- [ ] Markers used consistently: `@e2e`, `@snapshot`, `@slow`

## Design Notes

- **Textual Pilot** runs headless — no real terminal, fast execution, CI-friendly
- **pytest-textual-snapshot** produces SVG diffs — visual review without running the app
- Complements existing 17 unit tests in `brain/tests/test_command_centre/`
- Existing smoke tests (`test_tui_smoke.py`) serve as patterns for new E2E tests
- agent-browser reserved for web output testing (dashboards, HTML exports)

## Acceptance Criteria

- [ ] pytest-textual-snapshot installed and producing SVG snapshots
- [ ] At least 5 critical CC flows covered by Pilot E2E tests
- [ ] At least 3 visual snapshot tests covering core layouts
- [ ] All tests pass on a clean CC session
- [ ] Tests documented in `docs/TESTING.md`
- [ ] Data-loss bug (today list not saving on mutations) has a regression test

## Sub-tasks

- [ ] **OUT-329-A:** Install pytest-textual-snapshot, set up test directories and markers
- [ ] **OUT-329-B:** Write CC Pilot E2E tests (today list, command palette, help, session restore)
- [ ] **OUT-329-C:** Write visual snapshot tests (grid layout, help overlay, responsive)
- [ ] **OUT-329-D:** Document test strategy in `docs/TESTING.md`, wire into CI

## Related
- CC architecture: `docs/plans/2026-02-28-command-centre-architecture.md`
- CC bug review: `OUT-BUG-CC-REVIEW`
- Existing smoke tests: `brain/tests/test_command_centre/test_tui_smoke.py`
- agent-browser skill (for web outputs only): `.claude/skills/agent-browser/`
- Original inspiration: https://dev.to/hybridtechie/ai-regression-tests-written-in-markdown-not-code-5b09

## Progress Log
- 2026-03-09: Created PRD from task OUT-329
- 2026-03-09: PRD fleshed out — added CC E2E test requirements, agent-browser install task
- 2026-03-09: Pivoted from agent-browser to Textual Pilot + pytest-textual-snapshot after research confirmed agent-browser is browser-only and cannot test TUI apps
