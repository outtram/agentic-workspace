"""Persistent conversation log — every message and response written to dated files.

Logs live in brain/logs/conversations/YYYY-MM-DD.jsonl (one JSON object per line).
Each entry records: timestamp, direction (in/out), sender, chat_id, content, and
optionally the model used and latency.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs" / "conversations"


class ConversationLogger:
    """Append-only JSONL logger for all OutBot conversations."""

    def __init__(self, log_dir: Path | None = None) -> None:
        self._dir = log_dir or _LOG_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _file_for_today(self) -> Path:
        return self._dir / f"{datetime.now():%Y-%m-%d}.jsonl"

    def _write(self, record: dict) -> None:
        try:
            with self._file_for_today().open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("Failed to write conversation log")

    def log_incoming(
        self, chat_id: str, sender: str, content: str
    ) -> float:
        """Log an incoming user message. Returns a monotonic timestamp for latency tracking."""
        self._write({
            "ts": datetime.now().isoformat(),
            "dir": "in",
            "chat_id": chat_id,
            "sender": sender,
            "content": content,
        })
        return time.monotonic()

    def log_outgoing(
        self,
        chat_id: str,
        content: str,
        model: str = "",
        latency_s: float | None = None,
    ) -> None:
        """Log an outgoing bot response."""
        rec: dict = {
            "ts": datetime.now().isoformat(),
            "dir": "out",
            "chat_id": chat_id,
            "content": content,
        }
        if model:
            rec["model"] = model
        if latency_s is not None:
            rec["latency_s"] = round(latency_s, 2)
        self._write(rec)

    def log_error(
        self, chat_id: str, error: str, sender: str = ""
    ) -> None:
        """Log an error that occurred during message handling."""
        self._write({
            "ts": datetime.now().isoformat(),
            "dir": "error",
            "chat_id": chat_id,
            "sender": sender,
            "error": error,
        })
