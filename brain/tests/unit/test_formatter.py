"""Tests for WhatsApp message formatting."""

import pytest
from brain.personality.formatter import (
    strip_internal_tags,
    format_for_whatsapp,
    prefix_name,
    format_outbound,
)


class TestStripInternalTags:
    def test_removes_single_internal_tag(self):
        text = "<internal>thinking...</internal>Here is the answer."
        assert strip_internal_tags(text) == "Here is the answer."

    def test_removes_multiple_internal_tags(self):
        text = "<internal>step 1</internal>Result 1. <internal>step 2</internal>Result 2."
        assert strip_internal_tags(text) == "Result 1. Result 2."

    def test_handles_multiline_internal_tags(self):
        text = "<internal>\nDoing some\ncomplex reasoning\n</internal>\nThe answer is 42."
        assert strip_internal_tags(text) == "The answer is 42."

    def test_preserves_text_without_tags(self):
        text = "Just a normal message"
        assert strip_internal_tags(text) == "Just a normal message"

    def test_handles_empty_string(self):
        assert strip_internal_tags("") == ""


class TestFormatForWhatsapp:
    def test_converts_double_asterisks_to_single(self):
        assert "*bold*" in format_for_whatsapp("**bold**")
        assert "**" not in format_for_whatsapp("**bold**")

    def test_removes_markdown_headers(self):
        result = format_for_whatsapp("## My Header")
        assert "##" not in result
        assert "*My Header*" in result

    def test_converts_markdown_links(self):
        result = format_for_whatsapp("[click here](https://example.com)")
        assert "[" not in result
        assert "click here" in result
        assert "https://example.com" in result

    def test_converts_numbered_lists_to_bullets(self):
        result = format_for_whatsapp("1. First\n2. Second\n3. Third")
        assert "\u2022" in result
        assert "1." not in result

    def test_converts_dash_bullets(self):
        result = format_for_whatsapp("- Item one\n- Item two")
        assert "\u2022 Item one" in result

    def test_handles_empty_string(self):
        assert format_for_whatsapp("") == ""

    def test_strips_internal_tags_first(self):
        text = "<internal>thinking</internal>**answer**"
        result = format_for_whatsapp(text)
        assert "internal" not in result
        assert "*answer*" in result


class TestPrefixName:
    def test_prefixes_in_group(self):
        assert prefix_name("Hello", in_group=True) == "OutBot: Hello"

    def test_no_prefix_in_dm(self):
        assert prefix_name("Hello", in_group=False) == "Hello"

    def test_empty_string(self):
        assert prefix_name("", in_group=True) == ""


class TestFormatOutbound:
    def test_full_pipeline(self):
        text = (
            "<internal>reasoning</internal>## Important Update\n"
            "**Troy**, here's what happened:\n"
            "1. Meeting moved to 2pm\n"
            "2. Email from Sarah"
        )
        result = format_outbound(text, in_group=True)

        assert result.startswith("OutBot: ")
        assert "##" not in result
        assert "**" not in result
        assert "<internal>" not in result
        assert "\u2022" in result
