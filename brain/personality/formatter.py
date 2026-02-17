"""Format messages for different output channels."""

import re
import shutil
import textwrap

ASSISTANT_NAME = "OutBot"

# ANSI escape codes
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
RESET = "\033[0m"


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


def format_for_terminal(text: str) -> str:
    """Format for terminal output with ANSI colours and proper wrapping."""
    if not text:
        return ""

    # Strip internal reasoning first
    text = strip_internal_tags(text)

    # Convert **bold** to ANSI bold
    text = re.sub(r"\*\*(.+?)\*\*", rf"{BOLD}\1{RESET}", text)

    # Convert *italic* to ANSI dim (no true italic in most terminals)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", rf"{DIM}\1{RESET}", text)

    # Convert markdown headers to bold + colour
    text = re.sub(
        r"^#{1,6}\s+(.+)$",
        rf"{BOLD}{CYAN}\1{RESET}",
        text,
        flags=re.MULTILINE,
    )

    # Convert markdown links [text](url) to "text (url)"
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", rf"\1 ({DIM}\2{RESET})", text)

    # Bullets: convert - to coloured bullet
    text = re.sub(r"^-\s+", f"  {GREEN}•{RESET} ", text, flags=re.MULTILINE)

    # Numbered lists: keep as-is but indent
    text = re.sub(r"^(\d+\.)\s+", rf"  \1 ", text, flags=re.MULTILINE)

    # Clean up excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Wrap long lines to terminal width
    width = shutil.get_terminal_size((80, 24)).columns - 4  # 4 chars margin
    wrapped_lines = []
    for line in text.split("\n"):
        if len(line) > width and not line.startswith("\033"):
            # Don't wrap lines that start with ANSI codes (headers, bullets)
            wrapped = textwrap.fill(line, width=width)
            wrapped_lines.append(wrapped)
        else:
            wrapped_lines.append(line)
    text = "\n".join(wrapped_lines)

    return text.strip()


def format_for_voice(text: str) -> str:
    """Strip all formatting for text-to-speech output."""
    if not text:
        return ""

    text = strip_internal_tags(text)

    # Remove all markdown formatting
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # **bold**
    text = re.sub(r"\*(.+?)\*", r"\1", text)        # *italic*
    text = re.sub(r"#{1,6}\s+", "", text)            # Headers
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # Links
    text = re.sub(r"^[-•]\s+", "", text, flags=re.MULTILINE)  # Bullets
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)  # Numbered lists
    text = re.sub(r"`([^`]+)`", r"\1", text)  # Inline code
    text = re.sub(r"```[\s\S]*?```", "", text)  # Code blocks

    # Clean up whitespace
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


def prefix_name(text: str, in_group: bool = False) -> str:
    """Prefix message with assistant name for group chats."""
    if not text:
        return ""
    if in_group:
        return f"{ASSISTANT_NAME}: {text}"
    return text


def format_outbound(
    text: str, channel: str = "whatsapp", in_group: bool = False
) -> str:
    """Full outbound formatting pipeline.

    Args:
        text: Raw response from Claude
        channel: One of "cli", "whatsapp", "voice"
        in_group: Whether this is a group chat (adds name prefix)
    """
    text = strip_internal_tags(text)

    if channel == "cli":
        text = format_for_terminal(text)
    elif channel == "voice":
        text = format_for_voice(text)
    else:
        text = format_for_whatsapp(text)

    text = prefix_name(text, in_group)
    return text
