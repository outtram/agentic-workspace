"""SQLite database for OutBot persistent storage."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .models import Message, ScheduledTask, Session

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id TEXT NOT NULL,
    chat_jid TEXT NOT NULL,
    sender TEXT NOT NULL,
    sender_name TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    is_from_me INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (id, chat_jid)
);

CREATE TABLE IF NOT EXISTS sessions (
    chat_jid TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT '',
    last_active TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id TEXT PRIMARY KEY,
    chat_jid TEXT NOT NULL,
    prompt TEXT NOT NULL,
    schedule_type TEXT NOT NULL,
    schedule_value TEXT NOT NULL,
    next_run TEXT,
    last_run TEXT,
    last_result TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    run_at TEXT NOT NULL,
    result TEXT,
    duration_ms INTEGER
);

CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


class Database:
    """SQLite database with WAL mode for OutBot storage."""

    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- Messages --

    def store_message(self, msg: Message) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO messages
               (id, chat_jid, sender, sender_name, content, timestamp, is_from_me)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (msg.id, msg.chat_jid, msg.sender, msg.sender_name,
             msg.content, msg.timestamp, int(msg.is_from_me)),
        )
        self._conn.commit()

    def get_messages_since(
        self, chat_jid: str, since_timestamp: str, limit: int = 100
    ) -> list[Message]:
        rows = self._conn.execute(
            """SELECT id, chat_jid, sender, sender_name, content, timestamp, is_from_me
               FROM messages
               WHERE chat_jid = ? AND timestamp >= ?
               ORDER BY timestamp ASC
               LIMIT ?""",
            (chat_jid, since_timestamp, limit),
        ).fetchall()
        return [
            Message(
                id=r[0], chat_jid=r[1], sender=r[2], sender_name=r[3],
                content=r[4], timestamp=r[5], is_from_me=bool(r[6]),
            )
            for r in rows
        ]

    def get_recent_messages(
        self, chat_jid: str, limit: int = 20
    ) -> list[Message]:
        """Get the most recent messages for a chat, ordered oldest-first."""
        rows = self._conn.execute(
            """SELECT id, chat_jid, sender, sender_name, content, timestamp, is_from_me
               FROM messages
               WHERE chat_jid = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (chat_jid, limit),
        ).fetchall()
        msgs = [
            Message(
                id=r[0], chat_jid=r[1], sender=r[2], sender_name=r[3],
                content=r[4], timestamp=r[5], is_from_me=bool(r[6]),
            )
            for r in rows
        ]
        msgs.reverse()
        return msgs

    # -- Sessions --

    def get_session(self, chat_jid: str) -> Optional[Session]:
        row = self._conn.execute(
            "SELECT chat_jid, session_id, created_at, last_active FROM sessions WHERE chat_jid = ?",
            (chat_jid,),
        ).fetchone()
        if not row:
            return None
        return Session(chat_jid=row[0], session_id=row[1],
                       created_at=row[2], last_active=row[3])

    def set_session(self, chat_jid: str, session_id: str) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT INTO sessions (chat_jid, session_id, created_at, last_active)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(chat_jid) DO UPDATE SET
                   session_id = excluded.session_id,
                   last_active = excluded.last_active""",
            (chat_jid, session_id, now, now),
        )
        self._conn.commit()

    # -- Scheduled Tasks --

    def get_due_tasks(self) -> list[ScheduledTask]:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        rows = self._conn.execute(
            """SELECT id, chat_jid, prompt, schedule_type, schedule_value,
                      status, next_run, last_run, last_result, created_at
               FROM scheduled_tasks
               WHERE status = 'active' AND next_run <= ?
               ORDER BY next_run ASC""",
            (now,),
        ).fetchall()
        return [
            ScheduledTask(
                id=r[0], chat_jid=r[1], prompt=r[2], schedule_type=r[3],
                schedule_value=r[4], status=r[5], next_run=r[6],
                last_run=r[7], last_result=r[8], created_at=r[9],
            )
            for r in rows
        ]

    def update_task_next_run(self, task_id: str, next_run: str) -> None:
        self._conn.execute(
            "UPDATE scheduled_tasks SET next_run = ? WHERE id = ?",
            (next_run, task_id),
        )
        self._conn.commit()

    def log_task_run(self, task_id: str, result: str, duration_ms: int) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO task_run_logs (task_id, run_at, result, duration_ms) VALUES (?, ?, ?, ?)",
            (task_id, now, result, duration_ms),
        )
        self._conn.execute(
            "UPDATE scheduled_tasks SET last_run = ?, last_result = ? WHERE id = ?",
            (now, result, task_id),
        )
        self._conn.commit()

    # -- Key-Value State --

    def get_state(self, key: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    def set_state(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()
