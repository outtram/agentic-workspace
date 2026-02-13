from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Type
from collections import defaultdict

@dataclass
class Event:
    """Base event class"""
    timestamp: datetime = field(default_factory=datetime.now)

# Work Item Events
@dataclass
class WorkItemCreated(Event):
    work_item_id: str = ""
    reminder_id: Optional[str] = None

@dataclass
class WorkItemUpdated(Event):
    work_item_id: str = ""
    changes: dict = field(default_factory=dict)

@dataclass
class WorkItemCompleted(Event):
    work_item_id: str = ""

@dataclass
class WorkItemDeleted(Event):
    work_item_id: str = ""

# Reminder Events
@dataclass
class ReminderPushed(Event):
    work_item_id: str = ""
    reminder_id: str = ""
    success: bool = True

@dataclass
class ReminderPulled(Event):
    reminder_id: str = ""
    work_item_id: Optional[str] = None

# Sync Events
@dataclass
class SyncStarted(Event):
    sync_type: str = "full"  # "push" | "pull" | "full"

@dataclass
class SyncCompleted(Event):
    pushed: int = 0
    pulled: int = 0
    conflicts: int = 0

@dataclass
class ConflictDetected(Event):
    work_item_id: str = ""
    reminder_id: str = ""
    work_item_modified: Optional[datetime] = None
    reminder_modified: Optional[datetime] = None

@dataclass
class ConflictResolved(Event):
    work_item_id: str = ""
    resolution: str = ""  # "work_item_wins" | "reminder_wins" | "manual_merge"

# Enrichment Events
@dataclass
class EnrichmentSuggested(Event):
    work_item_id: str = ""
    suggestions: dict = field(default_factory=dict)

@dataclass
class EnrichmentApplied(Event):
    work_item_id: str = ""
    applied: dict = field(default_factory=dict)


class EventBus:
    """Simple pub/sub event bus"""

    def __init__(self):
        self._subscribers: dict[Type[Event], list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: Type[Event], handler: Callable):
        """Subscribe handler to event type"""
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event):
        """Publish event to all subscribers"""
        for handler in self._subscribers[type(event)]:
            handler(event)

    def unsubscribe(self, event_type: Type[Event], handler: Callable):
        """Unsubscribe handler from event type"""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
