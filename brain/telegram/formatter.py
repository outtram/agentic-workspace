"""Format OutBot responses for Telegram.

Telegram supports a subset of HTML for formatting:
  <b>bold</b>, <i>italic</i>, <code>code</code>, <pre>pre</pre>
  <a href="url">link</a>

This is simpler than WhatsApp's custom formatting.
"""

import re


def format_for_telegram(text: str) -> str:
    """Convert markdown-style formatting to Telegram HTML."""
    if not text:
        return ""

    # Code blocks first (before inline code matching eats backticks)
    text = re.sub(r"```(?:\w+)?\n?([\s\S]*?)```", r"<pre>\1</pre>", text)

    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Bold (**text**)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Italic (*text*) — avoid matching inside tags
    text = re.sub(r"(?<!\w)\*([^*]+?)\*(?!\w)", r"<i>\1</i>", text)

    # Markdown headers → bold
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    # Markdown links → HTML links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    # Numbered lists → bullet points
    text = re.sub(r"^\d+\.\s+", "• ", text, flags=re.MULTILINE)

    # Dash bullets → bullet points
    text = re.sub(r"^-\s+", "• ", text, flags=re.MULTILINE)

    # Escape stray HTML entities that aren't part of our tags
    text = _escape_untagged_html(text)

    # Clean up excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _escape_untagged_html(text: str) -> str:
    """Escape & < > that aren't part of HTML tags we added.

    Telegram's HTML parser is strict — unescaped < or & outside tags
    will cause the message to fail. We escape them selectively.
    """
    allowed_tags = {"b", "i", "code", "pre", "a"}
    result = []
    i = 0
    while i < len(text):
        if text[i] == "<":
            # Check if this is one of our allowed HTML tags
            tag_match = re.match(r"</?(\w+)(?:\s[^>]*)?>", text[i:])
            if tag_match and tag_match.group(1) in allowed_tags:
                result.append(tag_match.group(0))
                i += len(tag_match.group(0))
                continue
            result.append("&lt;")
            i += 1
        elif text[i] == "&" and not text[i:].startswith("&amp;") and not text[i:].startswith("&lt;") and not text[i:].startswith("&gt;"):
            result.append("&amp;")
            i += 1
        else:
            result.append(text[i])
            i += 1
    return "".join(result)
