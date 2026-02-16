"""Tests for heartbeat scheduler."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from brain.core.config import Config
from brain.core.models import ScheduledTask
from brain.heartbeat.scheduler import HeartbeatScheduler


class TestCalculateNextRun:
    def test_cron_calculates_next(self):
        task = ScheduledTask(
            id="t1",
            chat_jid="test",
            prompt="check",
            schedule_type="cron",
            schedule_value="0 9 * * 1-5",
            created_at="2026-01-01T00:00:00Z",
        )
        result = HeartbeatScheduler._calculate_next_run(task)
        assert result is not None
        # Should be a valid ISO timestamp in the future
        dt = datetime.fromisoformat(result)
        assert dt > datetime.now(timezone.utc)

    def test_interval_adds_seconds(self):
        task = ScheduledTask(
            id="t2",
            chat_jid="test",
            prompt="check",
            schedule_type="interval",
            schedule_value="1800",
            created_at="2026-01-01T00:00:00Z",
        )
        before = datetime.now(timezone.utc)
        result = HeartbeatScheduler._calculate_next_run(task)
        after = datetime.now(timezone.utc)

        assert result is not None
        dt = datetime.fromisoformat(result)
        # Should be ~30 minutes from now
        assert dt >= before + timedelta(seconds=1799)
        assert dt <= after + timedelta(seconds=1801)

    def test_once_returns_none(self):
        task = ScheduledTask(
            id="t3",
            chat_jid="test",
            prompt="check",
            schedule_type="once",
            schedule_value="2026-02-15T17:00:00Z",
            created_at="2026-01-01T00:00:00Z",
        )
        result = HeartbeatScheduler._calculate_next_run(task)
        assert result is None

    def test_unknown_type_returns_none(self):
        task = ScheduledTask(
            id="t4",
            chat_jid="test",
            prompt="check",
            schedule_type="unknown",
            schedule_value="???",
            created_at="2026-01-01T00:00:00Z",
        )
        result = HeartbeatScheduler._calculate_next_run(task)
        assert result is None


class TestSchedulerQuietHours:
    @pytest.mark.asyncio
    async def test_skips_during_quiet_hours(self):
        config = MagicMock(spec=Config)
        config.is_quiet_hours.return_value = True
        config.max_concurrent_tasks = 3

        db = MagicMock()
        event_bus = MagicMock()

        scheduler = HeartbeatScheduler(config, db, event_bus)
        await scheduler._tick()

        # Should NOT query for due tasks during quiet hours
        db.get_due_tasks.assert_not_called()

    @pytest.mark.asyncio
    async def test_queries_outside_quiet_hours(self):
        config = MagicMock(spec=Config)
        config.is_quiet_hours.return_value = False
        config.max_concurrent_tasks = 3

        db = MagicMock()
        db.get_due_tasks.return_value = []
        event_bus = MagicMock()

        scheduler = HeartbeatScheduler(config, db, event_bus)
        await scheduler._tick()

        db.get_due_tasks.assert_called_once()


class TestSchedulerConcurrency:
    @pytest.mark.asyncio
    async def test_skips_when_max_concurrent_reached(self):
        config = MagicMock(spec=Config)
        config.is_quiet_hours.return_value = False
        config.max_concurrent_tasks = 2

        db = MagicMock()
        event_bus = MagicMock()

        scheduler = HeartbeatScheduler(config, db, event_bus)
        scheduler._active_tasks = {"a", "b"}  # Already at max
        await scheduler._tick()

        db.get_due_tasks.assert_not_called()

    def test_task_completed_removes_from_active(self):
        config = MagicMock(spec=Config)
        db = MagicMock()
        event_bus = MagicMock()

        scheduler = HeartbeatScheduler(config, db, event_bus)
        scheduler._active_tasks.add("task-1")
        scheduler.task_completed("task-1")

        assert "task-1" not in scheduler._active_tasks
