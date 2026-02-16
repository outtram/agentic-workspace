"""Session management - one session per chat, stored in SQLite."""

import logging
import uuid
from datetime import datetime, timezone

from brain.core.db import Database
from brain.core.events import EventBus, SessionEnded, SessionStarted
from brain.core.models import Session

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages conversation sessions per chat_jid."""

    def __init__(self, db: Database, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    def get_or_create_session(self, chat_jid: str) -> Session:
        """Get existing session or create a new one."""
        session = self.db.get_session(chat_jid)
        if session:
            # Update last_active
            now = datetime.now(timezone.utc).isoformat()
            self.db.set_session(chat_jid, session.session_id)
            session.last_active = now
            return session

        # Create new session
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self.db.set_session(chat_jid, session_id)

        session = Session(
            chat_jid=chat_jid,
            session_id=session_id,
            created_at=now,
            last_active=now,
        )
        self.event_bus.publish(
            SessionStarted(chat_jid=chat_jid, session_id=session_id)
        )
        logger.info("New session created for %s: %s", chat_jid, session_id)
        return session

    def end_session(self, chat_jid: str):
        """End a session (e.g., on daily reset)."""
        session = self.db.get_session(chat_jid)
        if session:
            self.event_bus.publish(
                SessionEnded(
                    chat_jid=chat_jid, session_id=session.session_id
                )
            )
            logger.info("Session ended for %s", chat_jid)

    def reset_all_sessions(self):
        """Reset all sessions (e.g., daily 4am reset)."""
        logger.info("Resetting all sessions")
        # The orchestrator will handle creating new sessions on next message
