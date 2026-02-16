"""Format messages for WhatsApp delivery."""

import re

ASSISTANT_NAME = "OutBot"


def strip_internal_tags(text: str) -> str:
    """Remove <internal>...</internal> tags from agent output."""
    return re.sub(r"<internal>[\s\S]*?</internal>", "", text).strip()


def format_for_whatsapp(text: str) -> str:
    """Convert markdown-style formatting to WhatsApp-native formatting."""
    if not text:
        return ""

    # Strip internal reasoning first
    text = strip_internal_tags(text)

    # Convert **bold** to *bold* (WhatsApp uses single asterisks)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

    # Remove markdown headers (## Header -> just the text, bold)
    text = re.sub(r"^#{1,6}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # Convert markdown links [text](url) to "text: url"
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1: \2", text)

    # Convert numbered lists to bullet points
    text = re.sub(r"^\d+\.\s+", r"• ", text, flags=re.MULTILINE)

    # Convert - bullets to bullet points
    text = re.sub(r"^-\s+", r"• ", text, flags=re.MULTILINE)

    # Clean up excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def prefix_name(text: str, in_group: bool = False) -> str:
    """Prefix message with assistant name for group chats."""
    if not text:
        return ""
    if in_group:
        return f"{ASSISTANT_NAME}: {text}"
    return text


def format_outbound(text: str, in_group: bool = False) -> str:
    """Full outbound formatting pipeline."""
    text = strip_internal_tags(text)
    text = format_for_whatsapp(text)
    text = prefix_name(text, in_group)
    return text
