from pathlib import Path
from datetime import datetime
from typing import Optional
from reminders.core.events import EventBus, WorkItemCreated, WorkItemUpdated, WorkItemCompleted, WorkItemDeleted
from reminders.core.models import WorkItem
from reminders.adapters.workitems import WorkItemFileAdapter


class RemindersManager:
    """Main API for managing reminders - everything goes through this"""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        applescript_adapter=None,
        work_dir: Optional[Path] = None
    ):
        self.event_bus = event_bus or EventBus()
        if applescript_adapter is None:
            from reminders.adapters.applescript import AppleScriptAdapter
            applescript_adapter = AppleScriptAdapter()
        self.applescript = applescript_adapter
        self.workitems = WorkItemFileAdapter(work_dir=work_dir)
        self._next_id = self._get_next_work_item_id()

    def create_reminder(
        self,
        title: str,
        due_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        priority: str = "low",
        description: str = "",
        list_name: str = "Reminders"
    ) -> WorkItem:
        """Create a new reminder (work item + Reminders.app sync)"""
        work_item_id = f"OUT-{self._next_id}"
        self._next_id += 1

        # Classify into Eisenhower quadrant
        urgent = due_date is not None and priority in ["high", "urgent"]
        important = priority in ["high", "medium"] or bool(description)

        if urgent and important:
            quadrant = "q1"
        elif not urgent and important:
            quadrant = "q2"
        elif urgent and not important:
            quadrant = "q3"
        else:
            quadrant = "q4"

        now = datetime.now()
        work_item = WorkItem(
            id=work_item_id,
            title=title,
            status="todo",
            priority=priority,
            due_date=due_date,
            tags=tags or [],
            eisenhower_quadrant=quadrant,
            eisenhower_urgent=urgent,
            eisenhower_important=important,
            source="manual",
            description=description,
            created=now,
            updated=now
        )

        # Save work item file
        self.workitems.create(work_item)

        # Push to Reminders.app
        reminder_id = self.applescript.create_reminder(
            name=title,
            body=self._build_reminder_body(work_item),
            tags=tags,
            due_date=due_date,
            priority=self._map_priority_to_apple(priority),
            list_name=list_name
        )

        # Update work item with reminder_id
        work_item.reminder_id = reminder_id
        work_item.reminder_list = list_name
        self.workitems.update(work_item)

        # Emit event
        self.event_bus.publish(WorkItemCreated(
            work_item_id=work_item_id,
            reminder_id=reminder_id
        ))

        return work_item

    def import_reminder(
        self,
        title: str,
        reminder_id: str,
        due_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        priority: str = "low",
        description: str = "",
        list_name: str = "Reminders"
    ) -> WorkItem:
        """Import an existing reminder from Reminders.app (creates work item only, no sync back)"""
        work_item_id = f"OUT-{self._next_id}"
        self._next_id += 1

        # Classify into Eisenhower quadrant
        urgent = due_date is not None and priority in ["high", "urgent"]
        important = priority in ["high", "medium"] or bool(description)

        if urgent and important:
            quadrant = "q1"
        elif not urgent and important:
            quadrant = "q2"
        elif urgent and not important:
            quadrant = "q3"
        else:
            quadrant = "q4"

        now = datetime.now()
        work_item = WorkItem(
            id=work_item_id,
            title=title,
            status="todo",
            priority=priority,
            due_date=due_date,
            tags=tags or [],
            eisenhower_quadrant=quadrant,
            eisenhower_urgent=urgent,
            eisenhower_important=important,
            source="reminders_import",
            description=description,
            created=now,
            updated=now,
            reminder_id=reminder_id,
            reminder_list=list_name
        )

        # Save work item file only (no push to Reminders.app)
        self.workitems.create(work_item)

        # Emit event
        self.event_bus.publish(WorkItemCreated(
            work_item_id=work_item_id,
            reminder_id=reminder_id
        ))

        return work_item

    def complete_reminder(self, work_item_id: str):
        """Mark reminder as completed"""
        work_item = self.workitems.read(work_item_id)
        if not work_item:
            raise ValueError(f"Work item {work_item_id} not found")

        work_item.status = "done"
        work_item.updated = datetime.now()
        self.workitems.update(work_item)

        if work_item.reminder_id:
            try:
                self.applescript.update_reminder(
                    work_item.reminder_id,
                    completed=True
                )
            except (ValueError, RuntimeError):
                pass  # Reminder may have been deleted outside our system

        self.event_bus.publish(WorkItemCompleted(work_item_id=work_item_id))

    def delete_reminder(self, work_item_id: str):
        """Delete reminder from both systems"""
        work_item = self.workitems.read(work_item_id)
        if not work_item:
            raise ValueError(f"Work item {work_item_id} not found")

        if work_item.reminder_id:
            try:
                self.applescript.delete_reminder(work_item.reminder_id)
            except (ValueError, RuntimeError):
                pass  # Reminder may have been deleted outside our system

        self.workitems.delete(work_item_id)

        self.event_bus.publish(WorkItemDeleted(work_item_id=work_item_id))

    def list_reminders(
        self,
        tags: Optional[list[str]] = None,
        quadrant: Optional[str] = None,
        status: str = "todo"
    ) -> list[WorkItem]:
        """List reminders with optional filters"""
        all_items = self.workitems.list_all()

        items = [item for item in all_items if item.status == status]

        if tags:
            items = [
                item for item in items
                if any(tag in item.tags for tag in tags)
            ]

        if quadrant:
            items = [item for item in items if item.eisenhower_quadrant == quadrant]

        return items

    def get_reminder(self, work_item_id: str) -> Optional[WorkItem]:
        """Get single reminder by ID"""
        return self.workitems.read(work_item_id)

    def _get_next_work_item_id(self) -> int:
        """Find highest OUT-2XX ID and increment"""
        all_items = self.workitems.list_all()
        if not all_items:
            return 220

        highest = 220
        for item in all_items:
            if item.id.startswith("OUT-"):
                try:
                    num = int(item.id.split("-")[1])
                    if 200 <= num < 300:
                        highest = max(highest, num)
                except (ValueError, IndexError):
                    pass

        return highest + 1

    def _build_reminder_body(self, work_item: WorkItem) -> str:
        """Build reminder body with embedded metadata"""
        body = f"---\n{work_item.id}\n"
        body += f"eisenhower_quadrant: {work_item.eisenhower_quadrant}\n"
        body += f"branch: {work_item.branch}\n"
        body += "---\n"
        body += work_item.description
        return body

    def _map_priority_to_apple(self, priority: str) -> int:
        """Map priority string to Apple priority int"""
        mapping = {
            "high": 1,
            "urgent": 1,
            "medium": 5,
            "low": 9,
            "none": 0
        }
        return mapping.get(priority.lower(), 0)

    def _map_apple_priority_to_string(self, apple_priority: int) -> str:
        """Map Apple priority int to priority string"""
        mapping = {
            1: "high",
            5: "medium",
            9: "low",
            0: "low"
        }
        return mapping.get(apple_priority, "low")
