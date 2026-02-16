"""OutBot data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    """A WhatsApp message."""

    id: str
    chat_jid: str
    sender: str
    sender_name: str
    content: str
    timestamp: str
    is_from_me: bool = False


@dataclass
class Session:
    """An active conversation session with a chat."""

    chat_jid: str
    session_id: str
    created_at: str = ""
    last_active: str = ""


@dataclass
class ScheduledTask:
    """A recurring or one-off scheduled task."""

    id: str
    chat_jid: str
    prompt: str
    schedule_type: str   # 'cron' | 'interval' | 'once'
    schedule_value: str  # cron expr | seconds | ISO timestamp
    status: str = "active"  # 'active' | 'paused' | 'completed'
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    last_result: Optional[str] = None
    created_at: str = ""


@dataclass
class JudgementResult:
    """Result of a heartbeat judgement - should we notify Troy?"""

    should_notify: bool
    message: str = ""
    reasoning: str = ""
