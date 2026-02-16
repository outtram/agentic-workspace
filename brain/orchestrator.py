"""OutBot orchestrator - wires all components together and runs the main loop."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path

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
from brain.ipc.client import IPCClient
from brain.personality.formatter import format_outbound
from brain.personality.loader import PersonalityLoader
from brain.session.context import format_catchup_summary
from brain.session.manager import SessionManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main OutBot brain - routes messages, runs heartbeat, manages sessions."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.event_bus = EventBus()
        self.db = Database(config.db_path)
        self.ipc = IPCClient(config.socket_path, self.event_bus)
        self.sessions = SessionManager(self.db, self.event_bus)
        self.personality = PersonalityLoader(config.memory_dir)
        self.scheduler = HeartbeatScheduler(config, self.db, self.event_bus)
        self.claude = ClaudeClient()
        self.judge = ImportanceJudge(self.claude)
        self._whatsapp_proc: subprocess.Popen | None = None
        self._last_agent_ts: dict[str, str] = {}

    async def start(self) -> None:
        """Start all OutBot services."""
        logger.info("Starting OutBot orchestrator")

        # Subscribe to events
        self.event_bus.subscribe(MessageReceived, self._on_message_received)
        self.event_bus.subscribe(HeartbeatFired, self._on_heartbeat_fired)

        # Start WhatsApp Node.js subprocess
        self._start_whatsapp_process()

        # Give Node.js time to create the socket
        await asyncio.sleep(3)

        # Connect IPC client to WhatsApp service
        await self.ipc.connect(retries=10, delay=2.0)
        logger.info("Connected to WhatsApp service")

        # Start heartbeat scheduler as background task
        asyncio.create_task(self.scheduler.start())
        logger.info("Heartbeat scheduler running")

    async def stop(self) -> None:
        """Gracefully shut down all services."""
        logger.info("Stopping OutBot orchestrator")

        await self.scheduler.stop()
        await self.ipc.disconnect()

        if self._whatsapp_proc and self._whatsapp_proc.poll() is None:
            self._whatsapp_proc.terminate()
            try:
                self._whatsapp_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._whatsapp_proc.kill()

        self.db.close()
        logger.info("OutBot stopped")

    def _start_whatsapp_process(self) -> None:
        """Start the Node.js WhatsApp service as a subprocess."""
        whatsapp_dir = Path(__file__).parent / "whatsapp"
        if not (whatsapp_dir / "dist" / "index.js").exists():
            # Try tsx for development mode
            cmd = ["npx", "tsx", "src/index.ts"]
        else:
            cmd = ["node", "dist/index.js"]

        logger.info("Starting WhatsApp service: %s", " ".join(cmd))
        self._whatsapp_proc = subprocess.Popen(
            cmd,
            cwd=str(whatsapp_dir),
            stdout=None,   # Inherit terminal (QR code prints here)
            stderr=None,   # Inherit terminal (logs visible)
            env={
                **dict(__import__("os").environ),
                "OUTBOT_SOCKET_PATH": self.config.socket_path,
                "OUTBOT_PHONE_NUMBER": getattr(self.config, "phone_number", ""),
            },
        )

    def _on_message_received(self, event: MessageReceived) -> None:
        """Handle incoming WhatsApp message (sync handler, spawns async)."""
        if event.message and not event.message.is_from_me:
            asyncio.create_task(self._handle_message(event.message))

    async def _handle_message(self, msg: Message) -> None:
        """Process an incoming message through the full pipeline."""
        chat_jid = msg.chat_jid
        logger.info("Message from %s: %s", msg.sender_name, msg.content[:80])

        # Store the message
        self.db.store_message(msg)

        # Show typing indicator
        try:
            await self.ipc.set_typing(chat_jid, True)
        except Exception:
            pass

        try:
            # Get or create session
            session = self.sessions.get_or_create_session(chat_jid)

            # Gather missed messages for catch-up context
            since = self._last_agent_ts.get(chat_jid, "")
            missed = self.db.get_messages_since(chat_jid, since) if since else [msg]

            # Format catch-up context
            catchup = format_catchup_summary(missed)

            # Load personality
            personality = self.personality.load_personality()

            # Build prompt for Claude
            system_prompt = (
                f"{personality}\n\n"
                "You are responding via WhatsApp. Follow the formatting rules "
                "in your personality exactly. Keep responses concise."
            )

            user_content = catchup if catchup else msg.content

            # Call Claude via CLI (uses Max plan)
            reply_text = await self.claude.ask(
                prompt=user_content,
                system_prompt=system_prompt,
            )

            # Format for WhatsApp (strip internal tags, fix formatting)
            is_group = "@g.us" in chat_jid
            formatted = format_outbound(reply_text, in_group=is_group)

            if formatted:
                await self.ipc.send_message(chat_jid, formatted)
                self.event_bus.publish(
                    MessageSent(chat_jid=chat_jid, content=formatted)
                )

            # Update cursor
            self._last_agent_ts[chat_jid] = msg.timestamp

        except Exception:
            logger.exception("Failed to handle message from %s", chat_jid)
        finally:
            try:
                await self.ipc.set_typing(chat_jid, False)
            except Exception:
                pass

    def _on_heartbeat_fired(self, event: HeartbeatFired) -> None:
        """Handle heartbeat task firing (sync handler, spawns async)."""
        asyncio.create_task(self._run_heartbeat_task(event.task_id))

    async def _run_heartbeat_task(self, task_id: str) -> None:
        """Execute a heartbeat task: gather data, judge, notify if needed."""
        start = time.monotonic()
        logger.info("Running heartbeat task: %s", task_id)

        try:
            # Gather findings from integrations
            findings = await self._gather_heartbeat_findings()

            # Load checklist
            checklist = self.personality.load_heartbeat_checklist()

            # Judge importance
            result = await self.judge.judge(findings, checklist)
            self.event_bus.publish(
                HeartbeatResult(task_id=task_id, judgement=result)
            )

            # Notify if important
            if result.should_notify and result.message and self.config.troy_jid:
                formatted = format_outbound(result.message)
                await self.ipc.send_message(self.config.troy_jid, formatted)
                logger.info("Heartbeat notification sent: %s", result.reasoning)
            else:
                logger.debug("Heartbeat silent: %s", result.reasoning)

            # Log the run
            duration = int((time.monotonic() - start) * 1000)
            self.db.log_task_run(
                task_id, result.reasoning[:200], duration
            )

        except Exception:
            logger.exception("Heartbeat task %s failed", task_id)
        finally:
            self.scheduler.task_completed(task_id)

    async def _gather_heartbeat_findings(self) -> str:
        """Gather data from all integrations for heartbeat judgement."""
        sections = []

        # Reminders integration
        try:
            from brain.heartbeat.integrations.reminders_bridge import (
                format_reminders_for_judge,
                get_due_reminders,
            )

            reminders = get_due_reminders()
            sections.append(format_reminders_for_judge(reminders))
        except Exception as e:
            sections.append(f"Reminders: error - {e}")

        # Future: Gmail, Calendar integrations will be added here

        return "\n\n".join(sections) if sections else "No data gathered."
