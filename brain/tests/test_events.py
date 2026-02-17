"""Tests for EventBus — pub/sub decoupling."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.core.events import (
    EventBus,
    HeartbeatFired,
    MessageReceived,
    MessageSent,
    SessionStarted,
)
from brain.core.models import Message


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []

        bus.subscribe(MessageReceived, lambda e: received.append(e))
        bus.publish(MessageReceived(chat_jid="test@local"))

        assert len(received) == 1
        assert received[0].chat_jid == "test@local"

    def test_multiple_subscribers(self):
        bus = EventBus()
        results = {"a": [], "b": []}

        bus.subscribe(MessageSent, lambda e: results["a"].append(e))
        bus.subscribe(MessageSent, lambda e: results["b"].append(e))
        bus.publish(MessageSent(content="hello"))

        assert len(results["a"]) == 1
        assert len(results["b"]) == 1

    def test_event_type_isolation(self):
        bus = EventBus()
        received = []

        bus.subscribe(MessageReceived, lambda e: received.append("msg"))
        bus.subscribe(HeartbeatFired, lambda e: received.append("hb"))
        bus.publish(HeartbeatFired(task_id="t1"))

        assert received == ["hb"]

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        handler = lambda e: received.append(e)

        bus.subscribe(MessageReceived, handler)
        bus.publish(MessageReceived(chat_jid="1"))
        assert len(received) == 1

        bus.unsubscribe(MessageReceived, handler)
        bus.publish(MessageReceived(chat_jid="2"))
        assert len(received) == 1  # No new event

    def test_event_has_timestamp(self):
        event = SessionStarted(chat_jid="test", session_id="s1")
        assert event.timestamp is not None
