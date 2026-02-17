"""OutBot configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    """OutBot settings, loaded from .env file or environment."""

    socket_path: str = "/tmp/outbot.sock"
    db_path: str = "brain/store/outbot.db"
    quiet_start: int = 22  # 10pm - no proactive notifications after this
    quiet_end: int = 7     # 7am - notifications resume
    heartbeat_interval: int = 1800  # 30 minutes in seconds
    anthropic_api_key: str = ""  # Optional: only needed if using API directly
    troy_jid: str = ""
    max_concurrent_tasks: int = 3
    memory_dir: str = ".claude/memory"
    phone_number: str = ""
    email_backend: str = "console"
    email_address: str = ""
    email_app_password: str = ""
    email_default_to: str = ""

    @classmethod
    def load(cls, env_path: str | None = None) -> Config:
        """Load configuration from .env file and environment variables."""
        if env_path:
            load_dotenv(env_path)
        else:
            # Walk up from brain/ to find .env
            brain_dir = Path(__file__).parent.parent
            load_dotenv(brain_dir / ".env")

        return cls(
            socket_path=os.getenv("OUTBOT_SOCKET_PATH", "/tmp/outbot.sock"),
            db_path=os.getenv("OUTBOT_DB_PATH", "brain/store/outbot.db"),
            quiet_start=int(os.getenv("OUTBOT_QUIET_START", "22")),
            quiet_end=int(os.getenv("OUTBOT_QUIET_END", "7")),
            heartbeat_interval=int(os.getenv("OUTBOT_HEARTBEAT_INTERVAL", "1800")),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            troy_jid=os.getenv("OUTBOT_TROY_JID", ""),
            max_concurrent_tasks=int(os.getenv("OUTBOT_MAX_CONCURRENT_TASKS", "3")),
            memory_dir=os.getenv("OUTBOT_MEMORY_DIR", ".claude/memory"),
            phone_number=os.getenv("OUTBOT_PHONE_NUMBER", ""),
            email_backend=os.getenv("OUTBOT_EMAIL_BACKEND", "console"),
            email_address=os.getenv("OUTBOT_EMAIL_ADDRESS", ""),
            email_app_password=os.getenv("OUTBOT_EMAIL_APP_PASSWORD", ""),
            email_default_to=os.getenv("OUTBOT_EMAIL_DEFAULT_TO", ""),
        )

    def is_quiet_hours(self, hour: int | None = None) -> bool:
        """Check if current time is within quiet hours."""
        if hour is None:
            from datetime import datetime
            hour = datetime.now().hour
        if self.quiet_start > self.quiet_end:
            # Wraps midnight: e.g. 22-7 means 22,23,0,1,2,3,4,5,6
            return hour >= self.quiet_start or hour < self.quiet_end
        return self.quiet_start <= hour < self.quiet_end
