"""Telegram bridge — runs Telegram bot as background asyncio task in the TUI."""

import asyncio
import logging

logger = logging.getLogger(__name__)


class TelegramBridge:
    """Manages Telegram bot as a background task within the Command Centre."""

    def __init__(self):
        self.connected = False
        self._bot = None
        self._config = None
        self._event_bus = None
        self._on_message = None
        self.message_count = 0

    async def start(self, on_message=None):
        """Start Telegram bot in the background. Returns True on success."""
        self._on_message = on_message
        try:
            from brain.core.config import Config
            from brain.core.events import (
                EventBus,
                ConnectionChanged,
                MessageReceived,
            )
            from brain.telegram.bot import TelegramBot, TelegramConfig

            self._config = Config.load()
            if not self._config.telegram_token:
                logger.info("No Telegram token — bridge disabled")
                return False

            self._event_bus = EventBus()
            tg_config = TelegramConfig(
                token=self._config.telegram_token,
                troy_chat_id=self._config.telegram_chat_id,
            )
            self._bot = TelegramBot(tg_config, self._event_bus)

            self._event_bus.subscribe(
                ConnectionChanged, self._on_conn_changed
            )
            self._event_bus.subscribe(
                MessageReceived, self._on_msg_received
            )

            await self._bot.start()
            self.connected = True
            return True
        except Exception as e:
            logger.error("Telegram bridge failed to start: %s", e)
            return False

    async def stop(self):
        """Stop the Telegram bot."""
        if self._bot:
            await self._bot.stop()
            self.connected = False

    async def send(self, text: str) -> str:
        """Send a message via Telegram to Troy's chat."""
        if not self._bot or not self._config:
            return "[red]Telegram not configured[/]\nSet OUTBOT_TELEGRAM_TOKEN in brain/.env"
        if not self._config.telegram_chat_id:
            return "[red]No Telegram chat ID configured[/]\nSet OUTBOT_TELEGRAM_CHAT_ID in brain/.env"
        try:
            await self._bot.send_message(
                self._config.telegram_chat_id, text, parse_mode=""
            )
            return "[bold #00D4AA]Sent via Telegram[/]"
        except Exception as e:
            return f"[red]Telegram send failed: {e}[/]"

    @property
    def available(self) -> bool:
        return self._bot is not None

    @property
    def status_label(self) -> str:
        if not self.available:
            return ""
        return "TG: ON" if self.connected else "TG: OFF"

    def _on_conn_changed(self, event):
        self.connected = event.connected

    def _on_msg_received(self, event):
        if event.message and not event.message.is_from_me:
            self.message_count += 1
            if self._on_message:
                asyncio.create_task(self._on_message(event.message))
