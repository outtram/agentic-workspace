"""Archive session transcripts before context compaction."""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from brain.core.models import Message

logger = logging.getLogger(__name__)


class SessionArchiver:
    """Archives conversation transcripts as searchable markdown."""

    def __init__(self, archive_dir: str = "brain/store/conversations"):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def archive(
        self,
        chat_jid: str,
        messages: list[Message],
        summary: str = "",
    ) -> Path:
        """Archive messages as a dated markdown file.

        Args:
            chat_jid: The chat this transcript belongs to
            messages: Messages to archive
            summary: Optional topic summary for the filename

        Returns:
            Path to the created archive file
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H%M")

        # Sanitise summary for filename
        if summary:
            safe_summary = self._sanitise_filename(summary)
            filename = f"{date_str}-{time_str}-{safe_summary}.md"
        else:
            safe_jid = chat_jid.replace("@", "-").replace(".", "-")
            filename = f"{date_str}-{time_str}-{safe_jid}.md"

        filepath = self.archive_dir / filename

        # Format as markdown
        lines = []
        if summary:
            lines.append(f"# {summary}")
        else:
            lines.append("# Conversation Archive")

        lines.append(f"\nArchived: {now.strftime('%b %d, %I:%M %p')}")
        lines.append(f"Chat: {chat_jid}")
        lines.append("\n---\n")

        for msg in messages:
            name = msg.sender_name or msg.sender
            lines.append(f"**{name}**: {msg.content}")
            lines.append("")  # Blank line between messages

        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Archived %d messages to %s", len(messages), filepath)
        return filepath

    @staticmethod
    def _sanitise_filename(text: str) -> str:
        """Make text safe for use in filenames."""
        safe = re.sub(r"[^\w\s-]", "", text.lower())
        safe = re.sub(r"[\s]+", "-", safe)
        return safe[:50]
