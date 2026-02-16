"""Mock WhatsApp IPC server for Python-only testing."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path


class MockWhatsAppServer:
    """Fake UNIX socket IPC server that mimics the Node.js WhatsApp service.

    Use this for integration tests that don't need a real WhatsApp connection.
    Records all messages sent through it and can inject fake incoming messages.
    """

    def __init__(self, socket_path: str = "/tmp/outbot-test.sock") -> None:
        self.socket_path = socket_path
        self.sent_messages: list[dict] = []
        self.typing_states: dict[str, bool] = {}
        self._server: asyncio.Server | None = None
        self._client_writer: asyncio.StreamWriter | None = None

    async def start(self) -> None:
        """Start the mock IPC server."""
        # Remove stale socket
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        self._server = await asyncio.start_unix_server(
            self._handle_client, path=self.socket_path
        )

    async def stop(self) -> None:
        """Stop the mock server and clean up."""
        if self._client_writer:
            self._client_writer.close()
            try:
                await self._client_writer.wait_closed()
            except OSError:
                pass
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

    async def inject_message(
        self,
        chat_jid: str,
        sender: str,
        sender_name: str,
        content: str,
        timestamp: str = "2026-02-15T12:00:00Z",
    ) -> None:
        """Inject a fake incoming message notification."""
        if not self._client_writer:
            raise RuntimeError("No client connected")

        notification = {
            "jsonrpc": "2.0",
            "method": "message_received",
            "params": {
                "id": f"msg-{len(self.sent_messages)}",
                "chat_jid": chat_jid,
                "sender": sender,
                "sender_name": sender_name,
                "content": content,
                "timestamp": timestamp,
                "is_from_me": False,
            },
        }
        data = json.dumps(notification, separators=(",", ":")).encode() + b"\n"
        self._client_writer.write(data)
        await self._client_writer.drain()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a single client connection (the Python brain)."""
        self._client_writer = writer

        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                try:
                    msg = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                await self._handle_request(msg, writer)
        except asyncio.CancelledError:
            pass
        finally:
            self._client_writer = None

    async def _handle_request(
        self, msg: dict, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a JSON-RPC request from the brain."""
        method = msg.get("method", "")
        params = msg.get("params", {})
        msg_id = msg.get("id")

        if method == "send_message":
            self.sent_messages.append(params)
            response = {"jsonrpc": "2.0", "result": {"ok": True}, "id": msg_id}
        elif method == "set_typing":
            jid = params.get("chat_jid", "")
            self.typing_states[jid] = params.get("typing", False)
            response = {"jsonrpc": "2.0", "result": {"ok": True}, "id": msg_id}
        else:
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
                "id": msg_id,
            }

        data = json.dumps(response, separators=(",", ":")).encode() + b"\n"
        writer.write(data)
        await writer.drain()
