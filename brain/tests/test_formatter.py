"""Tests for personality formatter — markdown to WhatsApp conversion."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.personality.formatter import (
    format_for_terminal,
    format_for_voice,
    format_for_whatsapp,
    format_outbound,
    prefix_name,
    strip_internal_tags,
    BOLD,
    RESET,
    CYAN,
    GREEN,
    DIM,
)


class TestStripInternalTags:
    def test_removes_internal_block(self):
        text = "Hello <internal>thinking about stuff</internal> mate!"
        assert strip_internal_tags(text) == "Hello  mate!"

    def test_removes_multiline_internal(self):
        text = "Hi\n<internal>\nline1\nline2\n</internal>\nBye"
        result = strip_internal_tags(text)
        assert "<internal>" not in result
        assert "Hi" in result
        assert "Bye" in result

    def test_no_tags_unchanged(self):
        assert strip_internal_tags("just text") == "just text"

    def test_empty_string(self):
        assert strip_internal_tags("") == ""


class TestFormatForWhatsApp:
    def test_bold_double_to_single(self):
        assert format_for_whatsapp("**hello**") == "*hello*"

    def test_markdown_headers_to_bold(self):
        assert format_for_whatsapp("## My Header") == "*My Header*"
        assert format_for_whatsapp("# Big Header") == "*Big Header*"
        assert format_for_whatsapp("### Small Header") == "*Small Header*"

    def test_markdown_links_to_text_url(self):
        result = format_for_whatsapp("[Click here](https://example.com)")
        assert result == "Click here: https://example.com"

    def test_numbered_lists_to_bullets(self):
        result = format_for_whatsapp("1. First\n2. Second\n3. Third")
        assert result.startswith("• First")
        assert "• Second" in result
        assert "• Third" in result

    def test_dash_lists_to_bullets(self):
        result = format_for_whatsapp("- Item A\n- Item B")
        assert "• Item A" in result
        assert "• Item B" in result

    def test_excessive_newlines_collapsed(self):
        result = format_for_whatsapp("A\n\n\n\n\nB")
        assert result == "A\n\nB"

    def test_empty_string(self):
        assert format_for_whatsapp("") == ""

    def test_plain_text_unchanged(self):
        assert format_for_whatsapp("just some text") == "just some text"


class TestPrefixName:
    def test_no_prefix_in_dm(self):
        assert prefix_name("Hello", in_group=False) == "Hello"

    def test_prefix_in_group(self):
        assert prefix_name("Hello", in_group=True) == "OutBot: Hello"

    def test_empty_string(self):
        assert prefix_name("") == ""


class TestFormatForTerminal:
    def test_bold_to_ansi(self):
        result = format_for_terminal("**hello**")
        assert BOLD in result
        assert RESET in result
        assert "hello" in result
        assert "**" not in result

    def test_headers_to_bold_cyan(self):
        result = format_for_terminal("## My Header")
        assert BOLD in result
        assert CYAN in result
        assert "My Header" in result
        assert "##" not in result

    def test_bullets_get_colour(self):
        result = format_for_terminal("- Item A\n- Item B")
        assert GREEN in result
        assert "Item A" in result

    def test_empty_string(self):
        assert format_for_terminal("") == ""

    def test_plain_text_unchanged(self):
        result = format_for_terminal("just some text")
        assert "just some text" in result

    def test_links_formatted(self):
        result = format_for_terminal("[Click](https://example.com)")
        assert "Click" in result
        assert "https://example.com" in result
        # Markdown link syntax should be gone (but ANSI codes contain [)
        assert "](https" not in result


class TestFormatForVoice:
    def test_strips_bold(self):
        assert "**" not in format_for_voice("**hello** mate")
        assert "hello" in format_for_voice("**hello** mate")

    def test_strips_headers(self):
        result = format_for_voice("## Header\nSome text")
        assert "##" not in result
        assert "Header" in result

    def test_strips_bullets(self):
        result = format_for_voice("- First\n- Second")
        assert "- " not in result
        assert "First" in result

    def test_strips_code_blocks(self):
        result = format_for_voice("```python\nprint('hi')\n```")
        assert "```" not in result

    def test_strips_inline_code(self):
        result = format_for_voice("Use `pip install`")
        assert "`" not in result
        assert "pip install" in result

    def test_strips_links(self):
        result = format_for_voice("[Click](https://example.com)")
        assert "Click" in result
        assert "https" not in result

    def test_empty_string(self):
        assert format_for_voice("") == ""


class TestFormatOutbound:
    def test_full_pipeline_whatsapp(self):
        text = "<internal>reasoning</internal>**Hey** Troy! Check [this](https://x.com)"
        result = format_outbound(text)
        assert "<internal>" not in result
        assert "**" not in result
        assert "*Hey*" in result
        assert "this: https://x.com" in result

    def test_full_pipeline_cli(self):
        text = "**Hey** Troy!"
        result = format_outbound(text, channel="cli")
        assert BOLD in result
        assert "Hey" in result

    def test_full_pipeline_voice(self):
        text = "**Hey** Troy! Check [this](https://x.com)"
        result = format_outbound(text, channel="voice")
        assert "**" not in result
        assert "https" not in result
        assert "Hey" in result

    def test_group_message(self):
        result = format_outbound("Hello mate", in_group=True)
        assert result.startswith("OutBot: ")

    def test_default_channel_is_whatsapp(self):
        """Default channel should be whatsapp for backward compat."""
        result = format_outbound("**bold**")
        assert "*bold*" in result
        assert BOLD not in result
