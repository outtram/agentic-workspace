import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from reminders.core.events import EventBus, WorkItemCreated, WorkItemUpdated, WorkItemCompleted, WorkItemDeleted
from reminders.core.models import WorkItem
from reminders.adapters.workitems import WorkItemFileAdapter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
from task_registry import TaskRegistry


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
        if work_dir:
            self.registry = TaskRegistry(
                work_dir=work_dir.parent,
                task_dir=work_dir,
            )
        else:
            self.registry = TaskRegistry()

    def create_reminder(
        self,
        title: str,
        due_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        priority: str = "low",
        description: str = "",
        list_name: str = "Reminders"
    ) -> Optional[WorkItem]:
        """Create a new reminder (work item + Reminders.app sync)"""
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

        # Registry handles dedup, ID assignment, and file creation
        work_item_id = self.registry.create_task(
            title=title,
            source="manual",
            description=description,
            priority=priority,
            due_date=due_date,
            tags=tags,
            list_name=list_name,
            eisenhower_quadrant=quadrant,
            eisenhower_urgent=urgent,
            eisenhower_important=important,
        )

        if work_item_id is None:
            return None  # Duplicate detected

        # Read back the work item created by the registry
        work_item = self.workitems.read(work_item_id)

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
    ) -> Optional[WorkItem]:
        """Import an existing reminder from Reminders.app (creates work item only, no sync back)"""
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

        # Registry handles dedup (by reminder_id and fuzzy title), ID assignment, and file creation
        work_item_id = self.registry.create_task(
            title=title,
            source="reminders_import",
            reminder_id=reminder_id,
            description=description,
            priority=priority,
            due_date=due_date,
            tags=tags,
            list_name=list_name,
            eisenhower_quadrant=quadrant,
            eisenhower_urgent=urgent,
            eisenhower_important=important,
        )

        if work_item_id is None:
            return None  # Duplicate detected — already imported

        # Read back the work item created by the registry
        work_item = self.workitems.read(work_item_id)

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

        # Registry handles both YAML and file update
        self.registry.update_status(work_item_id, "done")

        if work_item.reminder_id:
            try:
                self.applescript.update_reminder(
                    work_item.reminder_id,
                    completed=True
                )
            except (ValueError, RuntimeError):
                pass  # Reminder may have been deleted outside our system

        self.event_bus.publish(WorkItemCompleted(work_item_id=work_item_id))

    def reverse_sync(self, active_ios_reminder_ids: set[str], dry_run: bool = False) -> list[str]:
        """Mark local tasks as done if their iOS reminder is no longer active."""
        local_map = self.registry.active_entries_with_reminder_id()
        stale_ids = []
        for reminder_id, out_id in local_map.items():
            if reminder_id not in active_ios_reminder_ids:
                stale_ids.append(out_id)
                if not dry_run:
                    self.registry.update_status(out_id, "done")
                    self.event_bus.publish(WorkItemCompleted(work_item_id=out_id))
        return stale_ids

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
