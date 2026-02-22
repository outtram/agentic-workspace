"""JSON-RPC 2.0 protocol for OutBot IPC (Python brain <-> Node.js WhatsApp)."""

from __future__ import annotations

import json
from typing import Any, Optional

# Method names for brain -> whatsapp
SEND_MESSAGE = "send_message"
SET_TYPING = "set_typing"

# Method names for whatsapp -> brain
MESSAGE_RECEIVED = "message_received"
CONNECTION_STATUS = "connection_status"
QR_CODE = "qr_code"


def make_request(method: str, params: dict[str, Any], id: str) -> dict:
    """Create a JSON-RPC 2.0 request."""
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": id,
    }


def make_response(id: str, result: Any) -> dict:
    """Create a JSON-RPC 2.0 success response."""
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": id,
    }


def make_error(id: str, code: int, message: str) -> dict:
    """Create a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": id,
    }


def make_notification(method: str, params: dict[str, Any]) -> dict:
    """Create a JSON-RPC 2.0 notification (no id = no response expected)."""
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }


def encode(msg: dict) -> bytes:
    """Encode a message as newline-delimited JSON bytes."""
    return json.dumps(msg, separators=(",", ":")).encode("utf-8") + b"\n"


def decode(data: bytes) -> dict:
    """Decode a newline-delimited JSON message."""
    return json.loads(data.strip())
