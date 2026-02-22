"""OutBot entry point — python brain/main.py

Starts the Telegram bot with heartbeat scheduler.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from brain.core.config import Config
from brain.orchestrator import Orchestrator


def setup_logging() -> None:
    """Configure logging for OutBot."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def run() -> None:
    """Main async entry point."""
    config = Config.load()

    if not config.telegram_token:
        print("\n  Error: OUTBOT_TELEGRAM_TOKEN not set in brain/.env")
        print("  Get a token from @BotFather on Telegram:")
        print("    1. Open Telegram and search for @BotFather")
        print("    2. Send /newbot and follow the prompts")
        print("    3. Copy the token into brain/.env as OUTBOT_TELEGRAM_TOKEN=your_token")
        print()
        sys.exit(1)

    orchestrator = Orchestrator(config)

    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def handle_signal() -> None:
        logging.getLogger(__name__).info("Shutdown signal received")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    await orchestrator.start()

    print("\n  OutBot is running on Telegram.")
    print("  Send a message to your bot to start chatting.")
    if not config.telegram_chat_id:
        print("  Tip: Send /start to your bot, then check logs for your chat ID.")
        print("  Set OUTBOT_TELEGRAM_CHAT_ID in .env for proactive notifications.")
    print("  Press Ctrl+C to stop.\n")

    await shutdown_event.wait()
    await orchestrator.stop()


def main() -> None:
    """Sync entry point."""
    setup_logging()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
