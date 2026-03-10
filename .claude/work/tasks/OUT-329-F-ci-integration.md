---
id: OUT-329-F
title: "CC tests: CI integration — Makefile targets for selective test runs"
type: task
status: todo
priority: low
created: '2026-03-10'
updated: '2026-03-10'
parent: OUT-329
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
---

# CC Tests — CI Integration

## Description

Wire CC test suite into a repeatable CI-friendly runner. Add Makefile targets or scripts so tests can be run selectively by marker.

## Steps

- [ ] Add `make test-cc` target (all CC tests)
- [ ] Add `make test-cc-e2e` target (E2E only, `-m e2e`)
- [ ] Add `make test-cc-snapshots` target (visual regression, `-m snapshot`)
- [ ] Add `make test-cc-update-snapshots` for baseline refresh after intentional UI changes
- [ ] Consider GitHub Actions workflow for nightly runs

## Context

- All tests currently runnable via: `python3 -m pytest brain/tests/test_command_centre/ -x -q`
- Markers defined in `brain/pyproject.toml`
- Docs: `docs/TESTING.md`
