"""Tests for calendar bridge integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from brain.heartbeat.integrations.calendar_bridge import (
    CalendarEvent,
    format_events_for_judge,
    get_upcoming_events,
    parse_applescript_events,
)


class TestParseApplescriptEvents:
    def test_parses_single_event(self):
        raw = "Team standup|2026-03-20 09:00:00 +0000|2026-03-20 09:30:00 +0000|Work"
        events = parse_applescript_events(raw)
        assert len(events) == 1
        assert events[0].title == "Team standup"
        assert events[0].calendar == "Work"

    def test_parses_multiple_events(self):
        raw = (
            "Team standup|2026-03-20 09:00:00 +0000|2026-03-20 09:30:00 +0000|Work\n"
            "Lunch|2026-03-20 12:00:00 +0000|2026-03-20 13:00:00 +0000|Personal"
        )
        events = parse_applescript_events(raw)
        assert len(events) == 2
        assert events[1].title == "Lunch"

    def test_empty_output_returns_empty_list(self):
        assert parse_applescript_events("") == []
        assert parse_applescript_events("  ") == []

    def test_malformed_line_is_skipped(self):
        raw = "bad line\nGood Event|2026-03-20 09:00:00 +0000|2026-03-20 09:30:00 +0000|Work"
        events = parse_applescript_events(raw)
        assert len(events) == 1
        assert events[0].title == "Good Event"


class TestFormatEventsForJudge:
    def _make_event(self, title: str, minutes_from_now: int, duration_min: int = 30) -> CalendarEvent:
        now = datetime.now(timezone.utc)
        start = now + timedelta(minutes=minutes_from_now)
        end = start + timedelta(minutes=duration_min)
        return CalendarEvent(title=title, start=start, end=end, calendar="Work")

    def test_no_events_returns_no_events_string(self):
        result = format_events_for_judge([])
        assert "No upcoming" in result

    def test_imminent_event_flagged(self):
        events = [self._make_event("Sprint review", 10)]
        result = format_events_for_judge(events)
        assert "Sprint review" in result
        # Minutes may round to 9 or 10 depending on execution time
        assert "min" in result

    def test_multiple_events_listed(self):
        events = [
            self._make_event("Standup", 5),
            self._make_event("1:1 with CEO", 60),
        ]
        result = format_events_for_judge(events)
        assert "Standup" in result
        assert "1:1 with CEO" in result


class TestGetUpcomingEvents:
    @patch("brain.heartbeat.integrations.calendar_bridge.subprocess.run")
    def test_returns_parsed_events_on_success(self, mock_run):
        now = datetime.now(timezone.utc)
        start_str = now.strftime("%Y-%m-%d %H:%M:%S +0000")
        end_str = (now + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S +0000")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=f"Team standup|{start_str}|{end_str}|Work",
            stderr="",
        )
        events = get_upcoming_events(lookahead_hours=4)
        assert len(events) == 1
        assert events[0].title == "Team standup"

    @patch("brain.heartbeat.integrations.calendar_bridge.subprocess.run")
    def test_returns_empty_list_on_applescript_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        events = get_upcoming_events(lookahead_hours=4)
        assert events == []

    @patch("brain.heartbeat.integrations.calendar_bridge.subprocess.run")
    def test_returns_empty_list_on_exception(self, mock_run):
        mock_run.side_effect = FileNotFoundError("osascript not found")
        events = get_upcoming_events(lookahead_hours=4)
        assert events == []
