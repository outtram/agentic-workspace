"""Event bus for decoupled communication between OutBot components."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Type

from .models import JudgementResult, Message


# --- Base ---

@dataclass
class Event:
    """Base event with timestamp."""

    timestamp: datetime = field(default_factory=datetime.now)


class EventBus:
    """Publish-subscribe event bus for internal component communication."""

    def __init__(self) -> None:
        self._subscribers: dict[Type[Event], list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: Type[Event], handler: Callable) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        for handler in self._subscribers[type(event)]:
            handler(event)

    def unsubscribe(self, event_type: Type[Event], handler: Callable) -> None:
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)


# --- OutBot Events ---

@dataclass
class MessageReceived(Event):
    """New message received from WhatsApp."""

    chat_jid: str = ""
    message: Message | None = None


@dataclass
class MessageSent(Event):
    """Message sent to WhatsApp."""

    chat_jid: str = ""
    content: str = ""


@dataclass
class HeartbeatFired(Event):
    """A scheduled heartbeat has fired."""

    task_id: str = ""


@dataclass
class HeartbeatResult(Event):
    """Result from a heartbeat judgement."""

    task_id: str = ""
    judgement: JudgementResult | None = None


@dataclass
class SessionStarted(Event):
    """A conversation session has started."""

    chat_jid: str = ""
    session_id: str = ""


@dataclass
class SessionEnded(Event):
    """A conversation session has ended."""

    chat_jid: str = ""
    session_id: str = ""


@dataclass
class ConnectionChanged(Event):
    """WhatsApp connection status changed."""

    connected: bool = False


@dataclass
class EmailSent(Event):
    """An email was sent via the outbox."""

    to: str = ""
    subject: str = ""
    msg_id: str = ""


@dataclass
class EmailReceived(Event):
    """A new email was received via inbox check."""

    sender: str = ""
    subject: str = ""
    msg_id: str = ""
