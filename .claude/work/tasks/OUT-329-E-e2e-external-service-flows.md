---
id: OUT-329-E
title: "CC E2E tests: external-service flows (sync, email, Eisenhower, session)"
type: task
status: todo
priority: low
category: tech
created: '2026-03-10'
updated: '2026-03-23'
parent: OUT-329
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
enriched: true
---

# CC E2E Tests — External Service Flows

## Description

Add Pilot E2E tests for CC flows that touch external services. These need heavier mocking than the core flow tests (OUT-329-B).

Follows from OUT-329 — foundation is in place, these are the remaining coverage gaps.

## Steps

- [ ] Write test: reminders sync — trigger sync, verify tasks appear in today list (mock RemindersManager)
- [ ] Write test: email import — `/import-emails` completes without crash (mock email bridge)
- [ ] Write test: Eisenhower dashboard — tasks appear in correct quadrants after filter
- [ ] Write test: session save/restore — quit CC, reopen, verify state persists (mock today.yml read/write)

## Context

- Test patterns: `brain/tests/test_command_centre/test_e2e/test_cc_flows.py`
- Mock fixture pattern: `mock_env` in same file
- Docs: `docs/TESTING.md`

## Progress Log
- 2026-03-23: Enriched in batch review. Preserved existing detail and replaced placeholders where needed.
