"""Tests for personality formatter — markdown to WhatsApp conversion."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.personality.formatter import (
    format_for_whatsapp,
    format_outbound,
    prefix_name,
    strip_internal_tags,
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


class TestFormatOutbound:
    def test_full_pipeline(self):
        text = "<internal>reasoning</internal>**Hey** Troy! Check [this](https://x.com)"
        result = format_outbound(text)
        assert "<internal>" not in result
        assert "**" not in result
        assert "*Hey*" in result
        assert "this: https://x.com" in result

    def test_group_message(self):
        result = format_outbound("Hello mate", in_group=True)
        assert result.startswith("OutBot: ")
