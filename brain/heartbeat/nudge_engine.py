"""Nudge engine — classifies heartbeat context into actionable nudge types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from brain.heartbeat.integrations.calendar_bridge import CalendarEvent, format_events_for_judge

# Meeting coming within this many minutes triggers PRE_MEETING nudge
PRE_MEETING_WINDOW_MINUTES = 15


class NudgeType(Enum):
    NONE = "none"
    PRE_MEETING = "pre_meeting"
    OVERDUE_TASKS = "overdue_tasks"
    MORNING_KICKOFF = "morning_kickoff"


@dataclass
class NudgeContext:
    upcoming_events: list[CalendarEvent] = field(default_factory=list)
    overdue_reminders: list[dict] = field(default_factory=list)
    hour_of_day: int = field(default_factory=lambda: datetime.now(timezone.utc).hour)
    is_morning_kickoff: bool = False


class NudgeEngine:
    """Classifies heartbeat context into a NudgeType with priority ordering."""

    def classify(self, ctx: NudgeContext) -> NudgeType:
        """Return the highest-priority nudge type for this context."""
        # 1. Imminent meeting beats everything
        if self._has_imminent_meeting(ctx.upcoming_events):
            return NudgeType.PRE_MEETING

        # 2. Morning kickoff (once per day, early window)
        if ctx.is_morning_kickoff:
            return NudgeType.MORNING_KICKOFF

        # 3. Overdue tasks
        if ctx.overdue_reminders:
            return NudgeType.OVERDUE_TASKS

        return NudgeType.NONE

    @staticmethod
    def _has_imminent_meeting(events: list[CalendarEvent]) -> bool:
        return any(ev.minutes_until() <= PRE_MEETING_WINDOW_MINUTES for ev in events)

    def build_findings_summary(self, ctx: NudgeContext) -> str:
        """Build a human-readable summary of the context for the importance judge."""
        parts = []

        events_section = format_events_for_judge(ctx.upcoming_events)
        parts.append(events_section)

        if ctx.overdue_reminders:
            lines = ["*Overdue / Due Tasks:*"]
            for r in ctx.overdue_reminders:
                due = f" (due: {r['due_date']})" if r.get("due_date") else ""
                priority = f" [{r['priority']}]" if r.get("priority") else ""
                lines.append(f"  • {r['title']}{priority}{due}")
            parts.append("\n".join(lines))
        else:
            parts.append("No overdue tasks.")

        nudge = self.classify(ctx)
        parts.append(f"*Nudge type:* {nudge.value}")

        return "\n\n".join(parts)
