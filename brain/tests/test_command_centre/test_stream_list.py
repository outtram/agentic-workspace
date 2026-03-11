"""Tests for StreamList widget rendering."""
from brain.command_centre.stream_list import render_stream_row


def _make_task(tid="OUT-1", state="new", title="Test Task", source="task", last_touched="2026-03-11T10:00:00"):
    return {
        "id": tid,
        "title": title,
        "stream_state": state,
        "source": source,
        "last_touched": last_touched,
        "snoozed_until": None,
    }


class TestRenderStreamRow:
    def test_new_item_has_green_dot(self):
        row = render_stream_row(_make_task(state="new"), focused=False)
        assert "●" in row
        assert "NEW" in row

    def test_seen_item_has_circle(self):
        row = render_stream_row(_make_task(state="seen"), focused=False)
        assert "○" in row
        assert "NEW" not in row

    def test_back_item_has_open_circle(self):
        row = render_stream_row(_make_task(state="back"), focused=False)
        assert "◌" in row
        assert "BACK" in row

    def test_focused_item_has_cursor(self):
        row = render_stream_row(_make_task(), focused=True)
        assert "▸" in row

    def test_title_in_output(self):
        row = render_stream_row(_make_task(title="My Task"), focused=False)
        assert "My Task" in row

    def test_source_label_in_output(self):
        row = render_stream_row(_make_task(source="email"), focused=False)
        assert "email" in row
