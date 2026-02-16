"""Integration test: full heartbeat cycle with mocked clock and Claude CLI."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from brain.core.claude_client import ClaudeClient
from brain.core.config import Config
from brain.core.db import Database
from brain.core.events import EventBus, HeartbeatFired, HeartbeatResult
from brain.core.models import JudgementResult, ScheduledTask
from brain.heartbeat.judge import ImportanceJudge
from brain.heartbeat.scheduler import HeartbeatScheduler

TEST_DB = ":memory:"


@pytest.fixture
def config():
    return Config(
        socket_path="/tmp/test.sock",
        db_path=TEST_DB,
        quiet_start=22,
        quiet_end=7,
        anthropic_api_key="test-key",
        troy_jid="troy@s.whatsapp.net",
    )


@pytest.fixture
def db():
    database = Database(TEST_DB)
    yield database
    database.close()


@pytest.fixture
def event_bus():
    return EventBus()


class TestHeartbeatCycle:
    def test_due_task_fires_event(self, config, db, event_bus):
        """A task whose next_run is in the past should fire HeartbeatFired."""
        # Insert a due task
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        db._conn.execute(
            """INSERT INTO scheduled_tasks
               (id, chat_jid, prompt, schedule_type, schedule_value,
                next_run, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("task-1", "troy@s.whatsapp.net", "Check reminders",
             "interval", "1800", past, "active", past),
        )
        db._conn.commit()

        fired = []
        event_bus.subscribe(HeartbeatFired, lambda e: fired.append(e))

        scheduler = HeartbeatScheduler(config, db, event_bus)

        # Mock quiet hours to be off
        with patch.object(config, "is_quiet_hours", return_value=False):
            asyncio.get_event_loop().run_until_complete(scheduler._tick())

        assert len(fired) == 1
        assert fired[0].task_id == "task-1"

    def test_quiet_hours_skips_tasks(self, config, db, event_bus):
        """Tasks should not fire during quiet hours."""
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        db._conn.execute(
            """INSERT INTO scheduled_tasks
               (id, chat_jid, prompt, schedule_type, schedule_value,
                next_run, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("task-2", "troy@s.whatsapp.net", "Check email",
             "interval", "1800", past, "active", past),
        )
        db._conn.commit()

        fired = []
        event_bus.subscribe(HeartbeatFired, lambda e: fired.append(e))

        scheduler = HeartbeatScheduler(config, db, event_bus)

        with patch.object(config, "is_quiet_hours", return_value=True):
            asyncio.get_event_loop().run_until_complete(scheduler._tick())

        assert len(fired) == 0

    def test_next_run_updated_after_fire(self, config, db, event_bus):
        """After firing, the task's next_run should be updated."""
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        db._conn.execute(
            """INSERT INTO scheduled_tasks
               (id, chat_jid, prompt, schedule_type, schedule_value,
                next_run, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("task-3", "troy@s.whatsapp.net", "Check tasks",
             "interval", "1800", past, "active", past),
        )
        db._conn.commit()

        scheduler = HeartbeatScheduler(config, db, event_bus)

        with patch.object(config, "is_quiet_hours", return_value=False):
            asyncio.get_event_loop().run_until_complete(scheduler._tick())

        # Check next_run was updated
        row = db._conn.execute(
            "SELECT next_run FROM scheduled_tasks WHERE id = 'task-3'"
        ).fetchone()
        assert row[0] is not None
        next_dt = datetime.fromisoformat(row[0])
        assert next_dt > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_judge_integration(self):
        """Test importance judge with mocked Claude CLI."""
        client = ClaudeClient()
        client.judge = AsyncMock(
            return_value='{"should_notify": true, "message": "*Meeting* with Sarah in 10 min!", "reasoning": "Imminent meeting"}'
        )
        judge = ImportanceJudge(client=client)

        result = await judge.judge(
            "Meeting with Sarah at 2:10pm. Current time: 2:00pm.",
            "Notify if meeting in <15 minutes.",
        )

        assert result.should_notify is True
        assert "Sarah" in result.message
        assert "Meeting" in result.message

    def test_max_concurrent_respected(self, config, db, event_bus):
        """Should not fire more tasks than max_concurrent_tasks."""
        config.max_concurrent_tasks = 1
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

        for i in range(3):
            db._conn.execute(
                """INSERT INTO scheduled_tasks
                   (id, chat_jid, prompt, schedule_type, schedule_value,
                    next_run, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"task-{i}", "troy@s.whatsapp.net", f"Task {i}",
                 "interval", "1800", past, "active", past),
            )
        db._conn.commit()

        fired = []
        event_bus.subscribe(HeartbeatFired, lambda e: fired.append(e))

        scheduler = HeartbeatScheduler(config, db, event_bus)

        with patch.object(config, "is_quiet_hours", return_value=False):
            # First tick: fires 1 (hits max)
            asyncio.get_event_loop().run_until_complete(scheduler._tick())

        assert len(fired) == 1

        # Mark first as complete, tick again
        scheduler.task_completed(fired[0].task_id)

        with patch.object(config, "is_quiet_hours", return_value=False):
            asyncio.get_event_loop().run_until_complete(scheduler._tick())

        assert len(fired) == 2
