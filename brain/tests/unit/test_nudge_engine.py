"""Tests for the proactive nudge engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from brain.heartbeat.integrations.calendar_bridge import CalendarEvent
from brain.heartbeat.nudge_engine import NudgeContext, NudgeEngine, NudgeType


def _event(title: str, minutes_from_now: int, duration_min: int = 30) -> CalendarEvent:
    now = datetime.now(timezone.utc)
    start = now + timedelta(minutes=minutes_from_now)
    end = start + timedelta(minutes=duration_min)
    return CalendarEvent(title=title, start=start, end=end, calendar="Work")


class TestNudgeType:
    def test_pre_meeting_nudge_for_imminent_event(self):
        engine = NudgeEngine()
        ctx = NudgeContext(
            upcoming_events=[_event("Standup", 12)],
            overdue_reminders=[],
            hour_of_day=9,
        )
        nudge = engine.classify(ctx)
        assert nudge == NudgeType.PRE_MEETING

    def test_no_nudge_for_distant_event(self):
        engine = NudgeEngine()
        ctx = NudgeContext(
            upcoming_events=[_event("Review", 120)],
            overdue_reminders=[],
            hour_of_day=9,
        )
        nudge = engine.classify(ctx)
        assert nudge == NudgeType.NONE

    def test_overdue_nudge_for_overdue_reminders(self):
        engine = NudgeEngine()
        ctx = NudgeContext(
            upcoming_events=[],
            overdue_reminders=[{"id": "OUT-1", "title": "Fix bug", "due_date": "2026-03-19"}],
            hour_of_day=10,
        )
        nudge = engine.classify(ctx)
        assert nudge == NudgeType.OVERDUE_TASKS

    def test_pre_meeting_takes_priority_over_overdue(self):
        engine = NudgeEngine()
        ctx = NudgeContext(
            upcoming_events=[_event("Board meeting", 8)],
            overdue_reminders=[{"id": "OUT-1", "title": "Fix bug", "due_date": "2026-03-19"}],
            hour_of_day=10,
        )
        nudge = engine.classify(ctx)
        assert nudge == NudgeType.PRE_MEETING

    def test_morning_kickoff_at_9am_with_no_events(self):
        engine = NudgeEngine()
        ctx = NudgeContext(
            upcoming_events=[],
            overdue_reminders=[],
            hour_of_day=9,
            is_morning_kickoff=True,
        )
        nudge = engine.classify(ctx)
        assert nudge == NudgeType.MORNING_KICKOFF

    def test_none_when_nothing_notable(self):
        engine = NudgeEngine()
        ctx = NudgeContext(
            upcoming_events=[],
            overdue_reminders=[],
            hour_of_day=14,
        )
        nudge = engine.classify(ctx)
        assert nudge == NudgeType.NONE


class TestNudgeContextSummary:
    def test_summary_includes_event_name(self):
        engine = NudgeEngine()
        ctx = NudgeContext(
            upcoming_events=[_event("Sprint planning", 10)],
            overdue_reminders=[],
            hour_of_day=9,
        )
        summary = engine.build_findings_summary(ctx)
        assert "Sprint planning" in summary

    def test_summary_includes_overdue_tasks(self):
        engine = NudgeEngine()
        ctx = NudgeContext(
            upcoming_events=[],
            overdue_reminders=[{"id": "OUT-5", "title": "Call accountant", "due_date": "2026-03-18"}],
            hour_of_day=11,
        )
        summary = engine.build_findings_summary(ctx)
        assert "Call accountant" in summary
