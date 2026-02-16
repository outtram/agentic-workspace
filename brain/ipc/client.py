"""Async UNIX socket client for communicating with the Node.js WhatsApp service."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from ..core.events import (
    ConnectionChanged,
    EventBus,
    MessageReceived,
)
from ..core.models import Message
from . import protocol

log = logging.getLogger(__name__)


class IPCClient:
    """Connects to the Node.js WhatsApp service over a UNIX socket.

    Messages are newline-delimited JSON-RPC 2.0.
    """

    def __init__(self, socket_path: str, event_bus: EventBus) -> None:
        self._socket_path = socket_path
        self._event_bus = event_bus
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._read_task: Optional[asyncio.Task] = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self, retries: int = 5, delay: float = 2.0) -> None:
        """Connect to the UNIX socket with retry and exponential backoff."""
        for attempt in range(1, retries + 1):
            try:
                self._reader, self._writer = await asyncio.open_unix_connection(
                    self._socket_path
                )
                self._connected = True
                self._read_task = asyncio.create_task(self._read_loop())
                self._event_bus.publish(ConnectionChanged(connected=True))
                log.info("Connected to WhatsApp service at %s", self._socket_path)
                return
            except (ConnectionRefusedError, FileNotFoundError, OSError) as exc:
                log.warning(
                    "Connection attempt %d/%d failed: %s", attempt, retries, exc
                )
                if attempt < retries:
                    await asyncio.sleep(delay * (2 ** (attempt - 1)))

        raise ConnectionError(
            f"Failed to connect to {self._socket_path} after {retries} attempts"
        )

    async def disconnect(self) -> None:
        """Clean disconnect from the socket."""
        self._connected = False
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except OSError:
                pass
        self._reader = None
        self._writer = None
        self._event_bus.publish(ConnectionChanged(connected=False))
        log.info("Disconnected from WhatsApp service")

    async def send_message(self, chat_jid: str, text: str) -> None:
        """Send a WhatsApp message via the Node.js service."""
        msg = protocol.make_request(
            protocol.SEND_MESSAGE,
            {"chat_jid": chat_jid, "text": text},
            id=uuid.uuid4().hex[:12],
        )
        await self._send(msg)

    async def set_typing(self, chat_jid: str, typing: bool) -> None:
        """Show or hide the typing indicator."""
        msg = protocol.make_request(
            protocol.SET_TYPING,
            {"chat_jid": chat_jid, "typing": typing},
            id=uuid.uuid4().hex[:12],
        )
        await self._send(msg)

    async def _read_loop(self) -> None:
        """Read incoming messages from the socket and publish events."""
        assert self._reader is not None
        try:
            while self._connected:
                line = await self._reader.readline()
                if not line:
                    log.warning("Socket closed by remote end")
                    self._connected = False
                    self._event_bus.publish(ConnectionChanged(connected=False))
                    break

                try:
                    data = protocol.decode(line)
                except Exception:
                    log.warning("Failed to decode message: %r", line[:200])
                    continue

                self._handle_incoming(data)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Error in IPC read loop")
            self._connected = False
            self._event_bus.publish(ConnectionChanged(connected=False))

    def _handle_incoming(self, data: dict) -> None:
        """Route an incoming JSON-RPC message to the appropriate event."""
        method = data.get("method")
        params = data.get("params", {})

        if method == protocol.MESSAGE_RECEIVED:
            msg = Message(
                id=params.get("id", ""),
                chat_jid=params.get("chat_jid", ""),
                sender=params.get("sender", ""),
                sender_name=params.get("sender_name", ""),
                content=params.get("content", ""),
                timestamp=params.get("timestamp", ""),
                is_from_me=params.get("is_from_me", False),
            )
            self._event_bus.publish(
                MessageReceived(chat_jid=msg.chat_jid, message=msg)
            )

        elif method == protocol.CONNECTION_STATUS:
            connected = params.get("connected", False)
            self._connected = connected
            self._event_bus.publish(ConnectionChanged(connected=connected))

        elif method == protocol.QR_CODE:
            qr_data = params.get("qr", "")
            log.info(
                "QR code received - scan with WhatsApp to authenticate"
                + (f" (data: {qr_data[:40]}...)" if qr_data else "")
            )

    async def _send(self, msg: dict) -> None:
        """Send a JSON-RPC message over the socket."""
        if not self._writer or not self._connected:
            raise ConnectionError("Not connected to WhatsApp service")
        self._writer.write(protocol.encode(msg))
        await self._writer.drain()
