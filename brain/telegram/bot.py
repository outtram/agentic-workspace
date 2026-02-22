"""Telegram Bot adapter for OutBot.

Uses the Telegram Bot API directly via httpx (no heavy framework needed).
Replaces the Node.js WhatsApp service + UNIX socket IPC with a simple
async polling loop that talks to Telegram's HTTP API.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from brain.core.events import ConnectionChanged, EventBus, MessageReceived
from brain.core.models import Message

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}"
POLL_TIMEOUT = 30  # Long-polling timeout in seconds


@dataclass
class TelegramConfig:
    """Telegram-specific configuration."""

    token: str
    troy_chat_id: str = ""
    allowed_chat_ids: list[str] | None = None


class TelegramBot:
    """Async Telegram bot using long-polling.

    Implements the same interface the orchestrator expects:
    - start() / stop() lifecycle
    - send_message(chat_id, text)
    - set_typing(chat_id) — sends "typing" chat action
    - Publishes MessageReceived events via EventBus
    """

    def __init__(self, config: TelegramConfig, event_bus: EventBus) -> None:
        self.config = config
        self.event_bus = event_bus
        self._base_url = API_BASE.format(token=config.token)
        self._client: Optional[httpx.AsyncClient] = None
        self._poll_task: Optional[asyncio.Task] = None
        self._offset: int = 0
        self._running = False
        self._bot_username: str = ""
        self._bot_id: int = 0

    async def start(self) -> None:
        """Connect to Telegram and start polling for updates."""
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(POLL_TIMEOUT + 10))
        self._running = True

        me = await self._api("getMe")
        self._bot_username = me.get("username", "")
        self._bot_id = me.get("id", 0)
        logger.info("Telegram bot connected: @%s (id: %d)", self._bot_username, self._bot_id)

        self.event_bus.publish(ConnectionChanged(connected=True))
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop polling and disconnect."""
        self._running = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()
            self._client = None
        self.event_bus.publish(ConnectionChanged(connected=False))
        logger.info("Telegram bot stopped")

    async def send_message(
        self, chat_id: str, text: str, parse_mode: str = "HTML"
    ) -> dict:
        """Send a message to a Telegram chat."""
        return await self._api(
            "sendMessage",
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
        )

    async def set_typing(self, chat_id: str, typing: bool = True) -> None:
        """Send 'typing' chat action."""
        if typing:
            try:
                await self._api("sendChatAction", chat_id=chat_id, action="typing")
            except Exception:
                pass

    async def _api(self, method: str, **params) -> dict:
        """Call a Telegram Bot API method."""
        assert self._client is not None
        url = f"{self._base_url}/{method}"
        resp = await self._client.post(url, json={k: v for k, v in params.items() if v is not None})
        data = resp.json()
        if not data.get("ok"):
            desc = data.get("description", "Unknown error")
            raise RuntimeError(f"Telegram API error: {desc}")
        return data.get("result", {})

    async def _poll_loop(self) -> None:
        """Long-poll for updates from Telegram."""
        logger.info("Telegram polling started")
        while self._running:
            try:
                updates = await self._get_updates()
                for update in updates:
                    self._offset = update["update_id"] + 1
                    self._handle_update(update)
            except asyncio.CancelledError:
                raise
            except httpx.ReadTimeout:
                continue
            except Exception:
                logger.exception("Telegram poll error, retrying in 5s")
                await asyncio.sleep(5)

    async def _get_updates(self) -> list[dict]:
        """Fetch updates using long-polling."""
        assert self._client is not None
        url = f"{self._base_url}/getUpdates"
        resp = await self._client.post(
            url,
            json={
                "offset": self._offset,
                "timeout": POLL_TIMEOUT,
                "allowed_updates": ["message"],
            },
        )
        data = resp.json()
        if not data.get("ok"):
            return []
        return data.get("result", [])

    def _handle_update(self, update: dict) -> None:
        """Convert a Telegram update into a MessageReceived event."""
        tg_msg = update.get("message")
        if not tg_msg:
            return

        text = tg_msg.get("text", "")
        if not text:
            caption = tg_msg.get("caption", "")
            if caption:
                text = caption
            else:
                return

        chat = tg_msg.get("chat", {})
        sender = tg_msg.get("from", {})
        chat_id = str(chat.get("id", ""))

        if self.config.allowed_chat_ids and chat_id not in self.config.allowed_chat_ids:
            logger.debug("Ignoring message from unauthorised chat: %s", chat_id)
            return

        is_from_me = sender.get("id") == self._bot_id
        is_group = chat.get("type") in ("group", "supergroup")

        if is_group:
            mentioned = self._is_bot_mentioned(text)
            is_reply_to_bot = self._is_reply_to_bot(tg_msg)
            if not mentioned and not is_reply_to_bot:
                return
            if mentioned:
                text = text.replace(f"@{self._bot_username}", "").strip()

        sender_name = sender.get("first_name", "")
        if sender.get("last_name"):
            sender_name += f" {sender['last_name']}"

        msg = Message(
            id=str(tg_msg.get("message_id", "")),
            chat_jid=chat_id,
            sender=str(sender.get("id", "")),
            sender_name=sender_name or sender.get("username", "unknown"),
            content=text,
            timestamp=str(tg_msg.get("date", "")),
            is_from_me=is_from_me,
        )

        if not is_from_me:
            logger.info("Message from %s: %s", msg.sender_name, msg.content[:80])
            self.event_bus.publish(
                MessageReceived(chat_jid=chat_id, message=msg)
            )

    def _is_bot_mentioned(self, text: str) -> bool:
        """Check if the bot is @mentioned in the text."""
        return self._bot_username and f"@{self._bot_username}" in text

    def _is_reply_to_bot(self, tg_msg: dict) -> bool:
        """Check if the message is a reply to the bot."""
        reply = tg_msg.get("reply_to_message")
        if not reply:
            return False
        reply_from = reply.get("from", {})
        return reply_from.get("id") == self._bot_id
