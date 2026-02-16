"""OutBot entry point - python brain/main.py"""

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
    # Quieten noisy libraries
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def run() -> None:
    """Main async entry point."""
    config = Config.load()

    orchestrator = Orchestrator(config)

    # Graceful shutdown on signals
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def handle_signal() -> None:
        logging.getLogger(__name__).info("Shutdown signal received")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    await orchestrator.start()

    print("\n  OutBot is running. Scan the QR code with WhatsApp to connect.")
    print("  Press Ctrl+C to stop.\n")

    # Wait for shutdown signal
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
