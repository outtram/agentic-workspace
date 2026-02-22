"""OutBot orchestrator - wires all components together and runs the main loop."""

from __future__ import annotations

import asyncio
import logging
import time

from brain.core.claude_client import ClaudeClient
from brain.core.config import Config
from brain.core.db import Database
from brain.core.events import (
    EventBus,
    HeartbeatFired,
    HeartbeatResult,
    MessageReceived,
    MessageSent,
)
from brain.core.models import Message
from brain.heartbeat.judge import ImportanceJudge
from brain.heartbeat.scheduler import HeartbeatScheduler
from brain.personality.formatter import format_outbound
from brain.personality.loader import PersonalityLoader
from brain.session.context import format_catchup_summary
from brain.session.manager import SessionManager
from brain.telegram.bot import TelegramBot, TelegramConfig

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main OutBot brain - routes messages, runs heartbeat, manages sessions."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.event_bus = EventBus()
        self.db = Database(config.db_path)
        self.sessions = SessionManager(self.db, self.event_bus)
        self.personality = PersonalityLoader(config.memory_dir)
        self.scheduler = HeartbeatScheduler(config, self.db, self.event_bus)
        self.claude = ClaudeClient()
        self.judge = ImportanceJudge(self.claude)
        self._last_agent_ts: dict[str, str] = {}

        tg_config = TelegramConfig(
            token=config.telegram_token,
            troy_chat_id=config.telegram_chat_id,
        )
        self.telegram = TelegramBot(tg_config, self.event_bus)

    async def start(self) -> None:
        """Start all OutBot services."""
        logger.info("Starting OutBot orchestrator")

        self.event_bus.subscribe(MessageReceived, self._on_message_received)
        self.event_bus.subscribe(HeartbeatFired, self._on_heartbeat_fired)

        await self.telegram.start()
        logger.info("Telegram bot connected")

        asyncio.create_task(self.scheduler.start())
        logger.info("Heartbeat scheduler running")

    async def stop(self) -> None:
        """Gracefully shut down all services."""
        logger.info("Stopping OutBot orchestrator")

        await self.scheduler.stop()
        await self.telegram.stop()

        self.db.close()
        logger.info("OutBot stopped")

    def _on_message_received(self, event: MessageReceived) -> None:
        """Handle incoming Telegram message (sync handler, spawns async)."""
        if event.message and not event.message.is_from_me:
            asyncio.create_task(self._handle_message(event.message))

    async def _handle_message(self, msg: Message) -> None:
        """Process an incoming message through the full pipeline."""
        chat_id = msg.chat_jid
        logger.info("Message from %s: %s", msg.sender_name, msg.content[:80])

        self.db.store_message(msg)

        await self.telegram.set_typing(chat_id)

        try:
            session = self.sessions.get_or_create_session(chat_id)

            since = self._last_agent_ts.get(chat_id, "")
            missed = self.db.get_messages_since(chat_id, since) if since else [msg]
            catchup = format_catchup_summary(missed)

            personality = self.personality.load_personality()

            system_prompt = (
                f"{personality}\n\n"
                "You are responding via Telegram. Follow the formatting rules "
                "in your personality exactly. Keep responses concise. "
                "Use HTML formatting: <b>bold</b>, <i>italic</i>, <code>code</code>."
            )

            user_content = catchup if catchup else msg.content

            reply_text = await self.claude.ask(
                prompt=user_content,
                system_prompt=system_prompt,
            )

            is_group = self._is_group_chat(msg)
            formatted = format_outbound(reply_text, channel="telegram", in_group=is_group)

            if formatted:
                await self.telegram.send_message(chat_id, formatted)
                self.event_bus.publish(
                    MessageSent(chat_jid=chat_id, content=formatted)
                )

            self._last_agent_ts[chat_id] = msg.timestamp

        except Exception:
            logger.exception("Failed to handle message from %s", msg.sender_name)

    def _is_group_chat(self, msg: Message) -> bool:
        """Detect if a message is from a group chat.

        Telegram group chat IDs are negative numbers.
        """
        try:
            return int(msg.chat_jid) < 0
        except (ValueError, TypeError):
            return False

    def _on_heartbeat_fired(self, event: HeartbeatFired) -> None:
        """Handle heartbeat task firing (sync handler, spawns async)."""
        asyncio.create_task(self._run_heartbeat_task(event.task_id))

    async def _run_heartbeat_task(self, task_id: str) -> None:
        """Execute a heartbeat task: gather data, judge, notify if needed."""
        start = time.monotonic()
        logger.info("Running heartbeat task: %s", task_id)

        try:
            findings = await self._gather_heartbeat_findings()
            checklist = self.personality.load_heartbeat_checklist()
            result = await self.judge.judge(findings, checklist)
            self.event_bus.publish(
                HeartbeatResult(task_id=task_id, judgement=result)
            )

            if result.should_notify and result.message and self.config.telegram_chat_id:
                formatted = format_outbound(result.message, channel="telegram")
                await self.telegram.send_message(
                    self.config.telegram_chat_id, formatted
                )
                logger.info("Heartbeat notification sent: %s", result.reasoning)
            else:
                logger.debug("Heartbeat silent: %s", result.reasoning)

            duration = int((time.monotonic() - start) * 1000)
            self.db.log_task_run(task_id, result.reasoning[:200], duration)

        except Exception:
            logger.exception("Heartbeat task %s failed", task_id)
        finally:
            self.scheduler.task_completed(task_id)

    async def _gather_heartbeat_findings(self) -> str:
        """Gather data from all integrations for heartbeat judgement."""
        sections = []

        try:
            from brain.heartbeat.integrations.reminders_bridge import (
                format_reminders_for_judge,
                get_due_reminders,
            )

            reminders = get_due_reminders()
            sections.append(format_reminders_for_judge(reminders))
        except Exception as e:
            sections.append(f"Reminders: error - {e}")

        return "\n\n".join(sections) if sections else "No data gathered."
