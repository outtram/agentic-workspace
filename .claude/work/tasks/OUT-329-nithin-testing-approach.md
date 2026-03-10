---
id: OUT-329
title: CC E2E regression testing — Textual Pilot + visual snapshots
type: task
status: todo
priority: low
created: '2026-03-09T21:49:23.380106'
updated: '2026-03-09T22:11:50.152017'
branch: task/OUT-329-nithin-testing-approach
source: reminders_import
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
reminder_id: x-apple-reminder://56C21886-F310-4384-BC6D-170E6E7036A2
reminder_list: Reminders
due_date: null
prd: OUT-329
---

# CC E2E Regression Testing

## Description

Extend CC test coverage with Textual Pilot E2E tests and pytest-textual-snapshot visual regression.

Original inspiration: https://dev.to/hybridtechie/ai-regression-tests-written-in-markdown-not-code-5b09

**Note:** agent-browser was the original plan but it's browser-only (Chromium). Cannot test Textual TUIs. Pivoted to native Textual testing tools.

## Steps

### OUT-329-A: Set up test infrastructure
- [ ] Install `pytest-textual-snapshot`
- [ ] Create `brain/tests/test_command_centre/test_e2e/` directory
- [ ] Create `brain/tests/test_command_centre/test_snapshots/` directory
- [ ] Add pytest markers: `@e2e`, `@snapshot`
- [ ] Document test strategy in `docs/TESTING.md`

### OUT-329-B: CC Pilot E2E Tests (critical flows)
- [ ] Write test: today list — add task, mark done, verify persistence
- [ ] Write test: command palette — open `/`, search, execute command
- [ ] Write test: help system — `?` renders help overlay correctly
- [ ] Write test: session restore — quit + reopen, state persists
- [ ] Run all E2E tests, confirm pass

### OUT-329-C: Visual Snapshot Tests
- [ ] Write snapshot: main grid layout at standard terminal size
- [ ] Write snapshot: help overlay
- [ ] Write snapshot: context panel with tile selected
- [ ] Write snapshot: responsive layout at small/medium/large sizes
- [ ] Write snapshot: command palette appearance

### OUT-329-D: CI Integration + Documentation
- [ ] Wire E2E tests into pytest run (with markers for selective execution)
- [ ] Document in `docs/TESTING.md`
- [ ] Add snapshot update instructions for when UI intentionally changes

## Research

- **agent-browser** — browser-only (Chromium accessibility tree). Cannot test terminal TUIs. Reserved for web output testing (dashboards, HTML exports).
- **Textual Pilot** — `App.run_test()` + `pilot` object. Simulates keypresses, clicks, queries widget state. Already working in `test_tui_smoke.py`. Fast, headless, CI-friendly.
- **pytest-textual-snapshot** — SVG visual regression. Captures screenshots, diffs between runs, produces HTML diff reports. Catches layout/styling breaks automatically.
- **Microsoft tui-test** — True PTY-based E2E. TypeScript, pre-release (v0.0.1-rc.5). Not recommended yet.
