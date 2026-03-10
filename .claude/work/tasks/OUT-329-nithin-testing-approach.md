---
id: OUT-329
title: CC E2E regression testing — Textual Pilot + visual snapshots
type: task
status: in-progress
priority: low
created: '2026-03-09T21:49:23.380106'
updated: '2026-03-10T00:00:00'
branch: task/OUT-329-nithin-testing-approach
source: reminders_import
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
reminder_id: x-apple-reminder://56C21886-F310-4384-BC6D-170E6E7036A2
reminder_list: Reminders
due_date: null
prd: OUT-329
children:
  - OUT-329-E
  - OUT-329-F
---

# CC E2E Regression Testing

## Description

Extend CC test coverage with Textual Pilot E2E tests and pytest-textual-snapshot visual regression.

Original inspiration: https://dev.to/hybridtechie/ai-regression-tests-written-in-markdown-not-code-5b09

**Note:** agent-browser was the original plan but it's browser-only (Chromium). Cannot test Textual TUIs. Pivoted to native Textual testing tools.

## Steps

### OUT-329-A: Set up test infrastructure — DONE
- [x] Install `pytest-textual-snapshot`
- [x] Create `brain/tests/test_command_centre/test_e2e/` directory
- [x] Create `brain/tests/test_command_centre/test_snapshots/` directory
- [x] Add pytest markers: `@e2e`, `@snapshot`
- [x] Document test strategy in `docs/TESTING.md`

### OUT-329-B: CC Pilot E2E Tests (critical flows) — DONE (core)
- [x] Write test: today list — add task, toggle remove, multi-select, persistence
- [x] Write test: command palette — open `/`, dismiss with Escape
- [x] Write test: help system — `?` renders help overlay correctly
- [x] Write test: grid navigation — arrows, number jump
- [x] Write test: selection — toggle, select all, deselect all
- [x] Write test: focus view — drill into leaf, escape back
- [x] Write test: escape cascade — modal → selection → quit
- [x] Run all 13 E2E tests, all pass

### OUT-329-C: Visual Snapshot Tests — DONE
- [x] Write snapshot: main grid layout (120x40)
- [x] Write snapshot: help overlay
- [x] Write snapshot: command palette
- [x] Write snapshot: filter picker
- [x] Write snapshot: focus view
- [x] Write snapshot: selected tile styling
- [x] Write snapshot: responsive small (80x24) and wide (200x50)
- [x] All 8 baselines generated and passing

### OUT-329-D: CI Integration + Documentation — PARTIAL
- [x] Document in `docs/TESTING.md`
- [x] Add snapshot update instructions
- [ ] Wire into CI script / Makefile → see OUT-329-F

## Remaining — see child tasks
- **OUT-329-E:** E2E tests for external-service flows (reminders sync, email import, Eisenhower, session restore)
- **OUT-329-F:** CI integration — Makefile target or script for selective test runs

## Research

- **agent-browser** — browser-only (Chromium accessibility tree). Cannot test terminal TUIs. Reserved for web output testing (dashboards, HTML exports).
- **Textual Pilot** — `App.run_test()` + `pilot` object. Simulates keypresses, clicks, queries widget state. Already working in `test_tui_smoke.py`. Fast, headless, CI-friendly.
- **pytest-textual-snapshot** — SVG visual regression. Captures screenshots, diffs between runs, produces HTML diff reports. Catches layout/styling breaks automatically.
- **Microsoft tui-test** — True PTY-based E2E. TypeScript, pre-release (v0.0.1-rc.5). Not recommended yet.
