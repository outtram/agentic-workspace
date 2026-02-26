"""OutBot orchestrator - wires all components together and runs the main loop."""

from __future__ import annotations

import asyncio
import logging
import re
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
from brain.mail.inbox import Inbox
from brain.mail.outbox import Outbox
from brain.memory.recall import format_recall_context, is_recall_trigger, search_memory
from brain.memory.remember import (
    extract_memory,
    forget_memory,
    is_forget_trigger,
    is_remember_trigger,
    write_memory,
)
from brain.personality.formatter import format_outbound
from brain.personality.loader import PersonalityLoader
from brain.session.context import format_catchup_summary
from brain.session.conversation_log import ConversationLogger
from brain.session.manager import SessionManager
from brain.telegram.bot import TelegramBot, TelegramConfig

logger = logging.getLogger(__name__)

_EMAIL_NOUNS = {"email", "emails", "mail", "inbox"}
_CHECK_VERBS = {"check", "read", "show", "get", "fetch", "see", "list", "any", "new", "latest", "recent", "look", "open", "view", "pull"}
_SEND_VERBS = {"send", "write", "compose", "draft", "fire"}

_TASK_NOUNS = {"task", "todo", "reminder", "item"}
_CREATE_VERBS = {"create", "add", "make", "new"}


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
        self.convo_log = ConversationLogger()
        self._last_agent_ts: dict[str, str] = {}

        self._inbox: Inbox | None = None
        self._outbox: Outbox | None = None
        if config.email_address and config.email_app_password:
            self._outbox = Outbox.from_config(config, event_bus=self.event_bus)
            self._inbox = Inbox.from_config(config)

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

    @staticmethod
    def _words(text: str) -> set:
        return set(re.findall(r"[a-z]+", text.lower()))

    def _is_email_check(self, text: str) -> bool:
        words = self._words(text)
        has_noun = bool(words & _EMAIL_NOUNS)
        has_verb = bool(words & _CHECK_VERBS)
        return "inbox" in words or (has_noun and has_verb)

    def _is_email_send(self, text: str) -> bool:
        words = self._words(text)
        return bool(words & _EMAIL_NOUNS) and bool(words & _SEND_VERBS)

    async def _fetch_emails(self, text: str) -> str:
        if not self._inbox:
            return "[Email not configured — set credentials in brain/.env]"
        try:
            words = self._words(text)
            unread_only = bool(words & {"unread", "new", "unseen"})
            emails = await self._inbox.check(limit=10, unread_only=unread_only)
        except Exception as e:
            hint = ""
            if "EOF" in str(e) or "AUTHENTICATIONFAILED" in str(e):
                hint = " (hint: enable IMAP in Gmail Settings)"
            return f"[Email check failed: {e}{hint}]"

        if not emails:
            label = "unread" if unread_only else "recent"
            return f"[No {label} emails in inbox]"

        label = "unread" if unread_only else "recent"
        lines = [f"[{len(emails)} {label} email(s) from inbox:]"]
        for i, e in enumerate(emails, 1):
            name = e.sender_name or e.sender
            preview = e.body[:200].replace("\n", " ") if e.body else "(no body)"
            lines.append(f"  {i}. From: {name} <{e.sender}>")
            lines.append(f"     Subject: {e.subject}")
            lines.append(f"     Date: {e.date}")
            lines.append(f"     Preview: {preview}")
        return "\n".join(lines)

    async def _send_email(self, text: str) -> str:
        if not self._outbox:
            return "[Email not configured — set credentials in brain/.env]"

        extraction = await self.claude.judge(
            prompt=text,
            system_prompt=(
                "Extract email details from the user's message. "
                "Reply in EXACTLY this format (one field per line):\n"
                "TO: <email address>\n"
                "SUBJECT: <subject line>\n"
                "BODY: <email body>\n\n"
                "If no recipient is specified, use TO: default\n"
                "If details are vague, make reasonable assumptions."
            ),
        )

        to_addr, subject, body = "", "", ""
        for line in extraction.strip().splitlines():
            line = line.strip()
            if line.upper().startswith("TO:"):
                to_addr = line[3:].strip()
            elif line.upper().startswith("SUBJECT:"):
                subject = line[8:].strip()
            elif line.upper().startswith("BODY:"):
                body = line[5:].strip()

        if to_addr.lower() == "default" or not to_addr:
            to_addr = self.config.email_default_to
            if not to_addr:
                return "[No recipient specified and OUTBOT_EMAIL_DEFAULT_TO not set]"

        if not subject:
            subject = "(no subject)"
        if not body:
            body = text

        try:
            await self._outbox.send(to=to_addr, subject=subject, body=body)
            return f'[Email SENT to {to_addr} — subject: "{subject}"]'
        except Exception as e:
            return f"[Email send FAILED: {e}]"

    @staticmethod
    def _is_daily_review(text: str) -> bool:
        """Check if the user wants to run the daily review."""
        lowered = text.lower().strip().rstrip("?!.")
        phrases = {
            "daily review", "daily-review", "do my daily review",
            "start my day", "daily priorities", "morning review",
            "import my reminders", "sync reminders",
            "what should i work on", "show me my q1",
        }
        return any(phrase in lowered for phrase in phrases)

    def _is_task_create(self, text: str) -> bool:
        """Check if the user wants to create a new task."""
        words = self._words(text)
        return bool(words & _TASK_NOUNS) and bool(words & _CREATE_VERBS)

    async def _create_task(self, text: str) -> str:
        """Extract task details via Claude haiku and create via TaskRegistry."""
        extraction = await self.claude.judge(
            prompt=text,
            system_prompt=(
                "Extract task details from the user's message. "
                "Reply in EXACTLY this format (one field per line):\n"
                "TITLE: <concise task title>\n"
                "PRIORITY: <low|medium|high>\n"
                "DUE: <YYYY-MM-DD or none>\n\n"
                "Examples:\n"
                "'create task to fix the van door by friday' → "
                "TITLE: Fix the van door / PRIORITY: medium / DUE: 2026-02-28\n"
                "'add a todo: research solar panels' → "
                "TITLE: Research solar panels / PRIORITY: low / DUE: none"
            ),
        )

        title, priority, due_date = "", "low", None
        for line in extraction.strip().splitlines():
            val = line.split(":", 1)[1].strip() if ":" in line else ""
            up = line.strip().upper()
            if up.startswith("TITLE:"):
                title = val
            elif up.startswith("PRIORITY:"):
                if val.lower() in ("low", "medium", "high"):
                    priority = val.lower()
            elif up.startswith("DUE:"):
                if val.lower() not in ("none", ""):
                    due_date = val

        if not title:
            return "[Could not extract task title from message]"

        try:
            import sys as _sys
            from pathlib import Path as _Path

            _scripts = _Path(__file__).resolve().parent.parent / ".claude" / "scripts"
            if str(_scripts) not in _sys.path:
                _sys.path.insert(0, str(_scripts))
            from task_registry import TaskRegistry

            registry = TaskRegistry()
            out_id = registry.create_task(
                title=title, source="outbot", priority=priority, due_date=due_date,
            )
            if out_id:
                return f'[TASK CREATED: {out_id} — "{title}" (priority: {priority})]'
            return f'[Task not created — duplicate detected for "{title}"]'
        except Exception as e:
            logger.error("Task creation failed: %s", e)
            return f"[Task creation failed: {e}]"

    def _build_conversation_history(self, chat_id: str, current_msg: Message) -> str:
        """Build multi-turn context from recent messages stored in the DB."""
        recent = self.db.get_recent_messages(chat_id, limit=20)
        if len(recent) <= 1:
            return ""

        lines = ["<conversation_history>"]
        for m in recent:
            role = "assistant" if m.is_from_me else "user"
            name = m.sender_name if not m.is_from_me else "OutBot"
            snippet = m.content[:500]
            lines.append(f'<msg role="{role}" from="{name}">{snippet}</msg>')
        lines.append("</conversation_history>")
        return "\n".join(lines)

    async def _handle_message(self, msg: Message) -> None:
        """Process an incoming message through the full pipeline."""
        chat_id = msg.chat_jid
        logger.info("Message from %s: %s", msg.sender_name, msg.content[:80])

        t0 = self.convo_log.log_incoming(chat_id, msg.sender_name, msg.content)
        self.db.store_message(msg)

        await self.telegram.set_typing(chat_id)

        try:
            session = self.sessions.get_or_create_session(chat_id)

            history = self._build_conversation_history(chat_id, msg)

            review_context = ""
            if self._is_daily_review(msg.content):
                try:
                    from brain.workflows.daily_review import run_daily_review
                    review_context = f"\n\n[DAILY REVIEW RESULTS]\n{run_daily_review()}"
                except Exception as e:
                    review_context = f"\n\n[Daily review failed: {e}]"
                    logger.error("Daily review failed: %s", e)

            email_context = ""
            if not review_context and self._is_email_check(msg.content):
                email_context = await self._fetch_emails(msg.content)
            elif not review_context and self._is_email_send(msg.content):
                email_context = await self._send_email(msg.content)

            # Memory: remember / forget
            memory_context = ""
            if is_remember_trigger(msg.content):
                try:
                    entry = await extract_memory(msg.content, self.claude)
                    saved = write_memory(entry, str(self.config.memory_dir))
                    memory_context = f"\n\n[MEMORY SAVED: {saved}]"
                except Exception as e:
                    memory_context = f"\n\n[Memory save failed: {e}]"
                    logger.error("Memory save failed: %s", e)
            elif is_forget_trigger(msg.content):
                try:
                    removed = await forget_memory(
                        msg.content, str(self.config.memory_dir), self.claude
                    )
                    if removed:
                        memory_context = "\n\n[Memory removed]"
                    else:
                        memory_context = "\n\n[No matching memory found]"
                except Exception as e:
                    memory_context = f"\n\n[Memory forget failed: {e}]"
                    logger.error("Memory forget failed: %s", e)

            # Recall: search past conversations
            recall_context = ""
            if is_recall_trigger(msg.content):
                try:
                    results = search_memory(
                        msg.content, str(self.config.memory_dir)
                    )
                    recall_context = format_recall_context(results)
                except Exception as e:
                    logger.warning("Recall search failed: %s", e)

            # Task creation
            task_context = ""
            if self._is_task_create(msg.content):
                task_context = await self._create_task(msg.content)

            personality = self.personality.load_personality()

            email_status = ""
            if self._outbox:
                email_status = (
                    f"\nYou CAN send and check email via {self._outbox.from_address}. "
                    "If email data appears below, summarise it naturally. "
                    "NEVER try to fetch email yourself — the data is already provided."
                )

            system_prompt = (
                f"{personality}\n\n"
                "You are responding via Telegram. Follow the formatting rules "
                "in your personality exactly. Keep responses concise. "
                "Use HTML formatting: <b>bold</b>, <i>italic</i>, <code>code</code>."
                f"{email_status}"
            )

            user_content = ""
            if history:
                user_content += f"{history}\n\n"
            user_content += msg.content
            if review_context:
                user_content += review_context
            if email_context:
                user_content += f"\n\n{email_context}"
            if memory_context:
                user_content += memory_context
            if recall_context:
                user_content += f"\n\n{recall_context}"
            if task_context:
                user_content += f"\n\n{task_context}"

            reply_text = await self.claude.ask(
                prompt=user_content,
                system_prompt=system_prompt,
            )

            latency = time.monotonic() - t0

            is_group = self._is_group_chat(msg)
            formatted = format_outbound(reply_text, channel="telegram", in_group=is_group)

            if formatted:
                await self.telegram.send_message(chat_id, formatted)
                self.event_bus.publish(
                    MessageSent(chat_jid=chat_id, content=formatted)
                )
                self.convo_log.log_outgoing(
                    chat_id, formatted,
                    model=self.claude.model, latency_s=latency,
                )

                bot_msg = Message(
                    id=f"bot-{msg.id}",
                    chat_jid=chat_id,
                    sender="outbot",
                    sender_name="OutBot",
                    content=formatted,
                    timestamp=msg.timestamp,
                    is_from_me=True,
                )
                self.db.store_message(bot_msg)

            self._last_agent_ts[chat_id] = msg.timestamp

        except RuntimeError as e:
            logger.exception("Failed to handle message from %s", msg.sender_name)
            self.convo_log.log_error(chat_id, str(e), msg.sender_name)
            error_hint = str(e)
            if "timed out" in error_hint.lower():
                user_msg = "Sorry mate, Claude took too long to respond. Try a simpler question or try again in a moment."
            else:
                user_msg = f"Something went wrong: {error_hint}"
            try:
                await self.telegram.send_message(chat_id, user_msg, parse_mode="")
            except Exception:
                logger.error("Could not send error message to Telegram")
        except Exception as exc:
            logger.exception("Failed to handle message from %s", msg.sender_name)
            self.convo_log.log_error(chat_id, str(exc), msg.sender_name)
            try:
                await self.telegram.send_message(
                    chat_id,
                    "Hit an unexpected error processing your message. Check the logs.",
                    parse_mode="",
                )
            except Exception:
                logger.error("Could not send error message to Telegram")

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
