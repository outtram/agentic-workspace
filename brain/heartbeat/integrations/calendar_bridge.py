"""Bridge to macOS Calendar.app via AppleScript for upcoming event awareness."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# AppleScript to list events in a time window.
# Returns pipe-delimited lines: title|start|end|calendar_name
_APPLESCRIPT = """\
set lookaheadHours to {hours}
set startDate to (current date)
set endDate to startDate + (lookaheadHours * 3600)

set output to ""
tell application "Calendar"
    repeat with aCal in calendars
        set calName to name of aCal
        set calEvents to (every event of aCal whose start date >= startDate and start date <= endDate)
        repeat with anEvent in calEvents
            set evTitle to summary of anEvent
            set evStart to start date of anEvent
            set evEnd to end date of anEvent
            set startStr to (evStart as string)
            set endStr to (evEnd as string)
            set output to output & evTitle & "|" & startStr & "|" & endStr & "|" & calName & "\\n"
        end repeat
    end repeat
end tell
return output
"""

# AppleScript date format: "Friday, 20 March 2026 at 09:00:00"
_AS_DATE_FMTS = [
    "%A, %d %B %Y at %H:%M:%S",
    "%Y-%m-%d %H:%M:%S +0000",  # fallback / test injection format
    "%Y-%m-%d %H:%M:%S +1000",  # AEST
    "%Y-%m-%d %H:%M:%S +1100",  # AEDT
]


@dataclass
class CalendarEvent:
    title: str
    start: datetime
    end: datetime
    calendar: str

    @property
    def duration_minutes(self) -> int:
        delta = self.end - self.start
        return max(0, int(delta.total_seconds() / 60))

    def minutes_until(self) -> int:
        now = datetime.now(timezone.utc)
        start = self.start if self.start.tzinfo else self.start.replace(tzinfo=timezone.utc)
        delta = start - now
        return max(0, int(delta.total_seconds() / 60))


def _parse_date(s: str) -> datetime | None:
    s = s.strip()
    for fmt in _AS_DATE_FMTS:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def parse_applescript_events(raw: str) -> list[CalendarEvent]:
    """Parse pipe-delimited AppleScript output into CalendarEvent objects."""
    events = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 4:
            logger.debug("Skipping malformed calendar line: %r", line)
            continue
        title, start_str, end_str, calendar = parts[0], parts[1], parts[2], parts[3]
        start = _parse_date(start_str)
        end = _parse_date(end_str)
        if start is None or end is None:
            logger.debug("Could not parse dates for event %r: %r / %r", title, start_str, end_str)
            continue
        events.append(CalendarEvent(title=title, start=start, end=end, calendar=calendar))
    return events


def get_upcoming_events(lookahead_hours: int = 4) -> list[CalendarEvent]:
    """Fetch upcoming calendar events from macOS Calendar.app.

    Args:
        lookahead_hours: How many hours ahead to look for events.

    Returns:
        List of CalendarEvent objects, empty on error.
    """
    script = _APPLESCRIPT.format(hours=lookahead_hours)
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning("Calendar AppleScript failed (rc=%d): %s", result.returncode, result.stderr[:200])
            return []
        return parse_applescript_events(result.stdout)
    except Exception as e:
        logger.warning("Calendar bridge error: %s", e)
        return []


def format_events_for_judge(events: list[CalendarEvent]) -> str:
    """Format upcoming events into a string for the importance judge."""
    if not events:
        return "No upcoming calendar events."

    lines = ["*Upcoming Calendar Events:*"]
    for ev in events:
        mins = ev.minutes_until()
        if mins < 60:
            timing = f"in {mins} min" if mins != 1 else "in 1 min"
        else:
            hours = mins // 60
            timing = f"in {hours}h"
        lines.append(f"  • {ev.title} ({ev.calendar}) — {timing}, {ev.duration_minutes}min long")
    return "\n".join(lines)
