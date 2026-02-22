"""Heartbeat scheduler - checks for due tasks every 60 seconds."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from croniter import croniter

from brain.core.config import Config
from brain.core.db import Database
from brain.core.events import EventBus, HeartbeatFired
from brain.core.models import ScheduledTask

logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # seconds


class HeartbeatScheduler:
    """Polls for due scheduled tasks and fires them."""

    def __init__(self, config: Config, db: Database, event_bus: EventBus):
        self.config = config
        self.db = db
        self.event_bus = event_bus
        self._running = False
        self._active_tasks: set[str] = set()  # Currently executing task IDs

    async def start(self):
        """Start the scheduler loop."""
        self._running = True
        logger.info("Heartbeat scheduler started (poll every %ds)", POLL_INTERVAL)
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error("Scheduler tick error: %s", e)
            await asyncio.sleep(POLL_INTERVAL)

    async def stop(self):
        """Stop the scheduler loop."""
        self._running = False
        logger.info("Heartbeat scheduler stopped")

    async def _tick(self):
        """One scheduler tick - check for due tasks."""
        # Skip during quiet hours (no proactive notifications)
        if self.config.is_quiet_hours():
            logger.debug("Quiet hours - skipping heartbeat tick")
            return

        # Enforce max concurrent tasks
        if len(self._active_tasks) >= self.config.max_concurrent_tasks:
            logger.debug(
                "Max concurrent tasks reached (%d), skipping",
                self.config.max_concurrent_tasks,
            )
            return

        due_tasks = self.db.get_due_tasks()
        for task in due_tasks:
            if task.id in self._active_tasks:
                continue  # Already running

            # Re-check concurrency limit before each task
            if len(self._active_tasks) >= self.config.max_concurrent_tasks:
                logger.debug("Max concurrent tasks reached mid-tick, stopping")
                break

            # Mark as active, fire event
            self._active_tasks.add(task.id)
            self.event_bus.publish(HeartbeatFired(task_id=task.id))

            # Calculate and update next_run
            next_run = self._calculate_next_run(task)
            self.db.update_task_next_run(task.id, next_run)

    def task_completed(self, task_id: str):
        """Mark a task as no longer active (called after execution)."""
        self._active_tasks.discard(task_id)

    @staticmethod
    def _calculate_next_run(task: ScheduledTask) -> str | None:
        """Calculate the next run time for a task."""
        now = datetime.now(timezone.utc)

        if task.schedule_type == "cron":
            cron = croniter(task.schedule_value, now)
            return cron.get_next(datetime).isoformat()

        elif task.schedule_type == "interval":
            seconds = int(task.schedule_value)
            return (now + timedelta(seconds=seconds)).isoformat()

        elif task.schedule_type == "once":
            return None  # No next run for one-shot tasks

        return None
