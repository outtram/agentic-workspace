"""OutBot core - configuration, models, events, and storage."""

from .claude_client import ClaudeClient
from .config import Config
from .db import Database
from .events import (
    ConnectionChanged,
    Event,
    EventBus,
    HeartbeatFired,
    HeartbeatResult,
    MessageReceived,
    MessageSent,
    SessionEnded,
    SessionStarted,
)
from .models import JudgementResult, Message, ScheduledTask, Session

__all__ = [
    "ClaudeClient",
    "Config",
    "ConnectionChanged",
    "Database",
    "Event",
    "EventBus",
    "HeartbeatFired",
    "HeartbeatResult",
    "JudgementResult",
    "Message",
    "MessageReceived",
    "MessageSent",
    "ScheduledTask",
    "Session",
    "SessionEnded",
    "SessionStarted",
]
