"""Format missed messages as XML catch-up context."""

from brain.core.models import Message


def escape_xml(text: str) -> str:
    """Escape XML special characters."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def format_catchup(messages: list[Message]) -> str:
    """Format missed messages as XML for agent context.

    Produces output like:
    <messages>
    <message sender="Troy" time="2026-02-15T14:30:00Z">hey</message>
    </messages>
    """
    if not messages:
        return ""

    lines = []
    for msg in messages:
        sender = escape_xml(msg.sender_name)
        content = escape_xml(msg.content)
        lines.append(
            f'<message sender="{sender}" time="{msg.timestamp}">'
            f"{content}</message>"
        )

    inner = "\n".join(lines)
    return f"<messages>\n{inner}\n</messages>"


def format_catchup_summary(
    messages: list[Message], max_messages: int = 50
) -> str:
    """Format catch-up with truncation for large backlogs.

    If more than max_messages, include first few, a gap note, and recent ones.
    """
    if len(messages) <= max_messages:
        return format_catchup(messages)

    # Show first 5 + last (max_messages - 10) with gap note
    head = messages[:5]
    tail = messages[-(max_messages - 10) :]
    skipped = len(messages) - len(head) - len(tail)

    head_lines = _format_lines(head)
    tail_lines = _format_lines(tail)

    return (
        f"<messages>\n{head_lines}\n"
        f'<gap count="{skipped}">...{skipped} messages skipped...</gap>\n'
        f"{tail_lines}\n</messages>"
    )


def _format_lines(messages: list[Message]) -> str:
    """Format a list of messages as XML lines (no outer wrapper)."""
    lines = []
    for msg in messages:
        sender = escape_xml(msg.sender_name)
        content = escape_xml(msg.content)
        lines.append(
            f'<message sender="{sender}" time="{msg.timestamp}">'
            f"{content}</message>"
        )
    return "\n".join(lines)
