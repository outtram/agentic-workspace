"""Heartbeat bridge — runs heartbeat scheduler as background asyncio task in the TUI."""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class HeartbeatBridge:
    """Manages the heartbeat scheduler as a background task within the Command Centre."""

    def __init__(self):
        self.running = False
        self.last_beat: float | None = None
        self._scheduler = None
        self._config = None
        self._db = None
        self._event_bus = None
        self._judge = None
        self._on_notification = None
        self._on_new_items = None  # Callback: async fn(message: str)
        self._task: asyncio.Task | None = None

    async def start(self, on_notification=None, on_new_items=None) -> bool:
        """Start the heartbeat scheduler in the background. Returns True on success."""
        self._on_notification = on_notification
        self._on_new_items = on_new_items
        try:
            from brain.core.config import Config
            from brain.core.db import Database
            from brain.core.events import EventBus, HeartbeatFired
            from brain.heartbeat.scheduler import HeartbeatScheduler
            from brain.heartbeat.judge import ImportanceJudge

            self._config = Config.load()
            self._db = Database(self._config.db_path)
            self._event_bus = EventBus()
            self._judge = ImportanceJudge()

            self._scheduler = HeartbeatScheduler(
                self._config, self._db, self._event_bus
            )

            # Subscribe to heartbeat events
            self._event_bus.subscribe(
                HeartbeatFired, self._on_heartbeat_fired
            )

            # Seed a default reminders check task if none exist
            self._seed_default_task()

            # Start scheduler as background task
            self._task = asyncio.create_task(self._scheduler.start())
            self.running = True
            logger.info("Heartbeat bridge started")
            return True
        except Exception as e:
            logger.error("Heartbeat bridge failed to start: %s", e)
            return False

    async def stop(self):
        """Stop the heartbeat scheduler."""
        if self._scheduler:
            await self._scheduler.stop()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._db:
            self._db.close()
        self.running = False
        logger.info("Heartbeat bridge stopped")

    @property
    def status_label(self) -> str:
        if not self.running:
            return ""
        return "BEAT: ON"

    def _seed_default_task(self):
        """Ensure at least one scheduled task exists for reminders checking.

        Uses direct DB access for one-time seed — no public method exists
        for counting active tasks (only get_due_tasks which filters by time).
        """
        from datetime import datetime, timezone

        # Check if any active tasks exist at all
        rows = self._db._conn.execute(
            "SELECT COUNT(*) FROM scheduled_tasks WHERE status = 'active'"
        ).fetchone()
        if rows[0] == 0:
            now = datetime.now(timezone.utc).isoformat()
            self._db._conn.execute(
                """INSERT INTO scheduled_tasks
                   (id, chat_jid, prompt, schedule_type, schedule_value, next_run, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "heartbeat-reminders",
                    "command-centre",
                    "Check for due and overdue reminders",
                    "interval",
                    "60",
                    now,
                    "active",
                    now,
                ),
            )
            self._db._conn.commit()
            logger.info("Seeded default heartbeat task: heartbeat-reminders")

    def _on_heartbeat_fired(self, event):
        """Handle a heartbeat event — gather findings and judge importance."""
        self.last_beat = time.time()
        asyncio.create_task(self._process_heartbeat(event.task_id))

    async def _process_heartbeat(self, task_id: str):
        """Gather findings, run importance judge, notify if needed."""
        try:
            from brain.heartbeat.integrations.reminders_bridge import (
                get_due_reminders,
                format_reminders_for_judge,
            )
            from pathlib import Path

            # Gather findings from reminders
            loop = asyncio.get_running_loop()
            reminders = await loop.run_in_executor(None, get_due_reminders)
            findings = format_reminders_for_judge(reminders)

            # Load heartbeat checklist
            checklist_path = Path(__file__).resolve().parents[2] / ".claude" / "memory" / "HEARTBEAT.md"
            checklist = ""
            if checklist_path.exists():
                checklist = checklist_path.read_text(encoding="utf-8")

            # Run importance judge
            result = await self._judge.judge(findings, checklist)

            # Mark task as completed in scheduler
            if self._scheduler:
                self._scheduler.task_completed(task_id)

            # Proactive email + reminder polling for stream view
            await self._poll_for_new_items()

            # Notify if important
            if result.should_notify and result.message and self._on_notification:
                await self._on_notification(result.message)

        except Exception as e:
            logger.error("Heartbeat processing failed: %s", e)
            if self._scheduler:
                self._scheduler.task_completed(task_id)

    async def _poll_for_new_items(self):
        """Check for new emails and reminders, notify if found."""
        messages = []

        # Email check (with timeout protection)
        try:
            from brain.core.config import Config
            from brain.mail.inbox import Inbox

            config = Config.load()
            if config.email_address and config.email_app_password:
                inbox = Inbox(config.email_address, config.email_app_password)
                emails = await inbox.check(limit=5, unread_only=True)
                if emails:
                    messages.append(f"✉ {len(emails)} new email{'s' if len(emails) != 1 else ''}")
        except Exception as e:
            logger.warning("Email poll failed: %s", e)

        if messages and self._on_new_items:
            await self._on_new_items(" · ".join(messages))
