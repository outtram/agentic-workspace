"""Tests for token usage tracking."""

import json
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.core.usage import UsageTracker, DEFAULT_DAILY_BUDGET


class TestUsageTracker:
    def test_record_accumulates_session(self, tmp_path):
        tracker = UsageTracker(store_dir=str(tmp_path))
        tracker.record({"input_tokens": 100, "output_tokens": 50}, cost_usd=0.01)
        tracker.record({"input_tokens": 200, "output_tokens": 80}, cost_usd=0.02)

        assert tracker.session_input == 300
        assert tracker.session_output == 130
        assert tracker.session_total == 430
        assert tracker.session_calls == 2
        assert abs(tracker.session_cost_usd - 0.03) < 0.001

    def test_record_persists_daily(self, tmp_path):
        tracker = UsageTracker(store_dir=str(tmp_path))
        tracker.record({"input_tokens": 1000, "output_tokens": 500}, cost_usd=0.1)

        # Check file was written
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1

        data = json.loads(files[0].read_text())
        assert data["input_tokens"] == 1000
        assert data["output_tokens"] == 500
        assert data["calls"] == 1

    def test_daily_accumulates_across_sessions(self, tmp_path):
        """Multiple tracker instances should accumulate the same day's usage."""
        t1 = UsageTracker(store_dir=str(tmp_path))
        t1.record({"input_tokens": 1000, "output_tokens": 500})

        t2 = UsageTracker(store_dir=str(tmp_path))
        t2.record({"input_tokens": 2000, "output_tokens": 800})

        assert t2.daily_total == 4300  # 1000+500+2000+800

    def test_daily_percent(self, tmp_path):
        tracker = UsageTracker(store_dir=str(tmp_path), daily_budget=100_000)
        tracker.record({"input_tokens": 25_000, "output_tokens": 25_000})

        assert tracker.daily_percent == 50.0

    def test_daily_percent_caps_at_100(self, tmp_path):
        tracker = UsageTracker(store_dir=str(tmp_path), daily_budget=1000)
        tracker.record({"input_tokens": 5000, "output_tokens": 5000})

        assert tracker.daily_percent == 100.0

    def test_format_status(self, tmp_path):
        tracker = UsageTracker(store_dir=str(tmp_path), daily_budget=264_000)
        tracker.record({"input_tokens": 5000, "output_tokens": 3000})

        status = tracker.format_status()
        assert "session:" in status
        assert "today:" in status
        assert "%" in status

    def test_format_session_summary(self, tmp_path):
        tracker = UsageTracker(store_dir=str(tmp_path))
        tracker.record({"input_tokens": 10000, "output_tokens": 5000}, cost_usd=0.5)

        summary = tracker.format_session_summary()
        assert "15,000" in summary  # Total tokens
        assert "1 calls" in summary
        assert "$0.500" in summary
        assert "%" in summary

    def test_handles_missing_fields(self, tmp_path):
        """Should not crash if usage dict is incomplete."""
        tracker = UsageTracker(store_dir=str(tmp_path))
        tracker.record({})  # Empty usage dict

        assert tracker.session_total == 0
        assert tracker.session_calls == 1

    def test_handles_cache_tokens(self, tmp_path):
        tracker = UsageTracker(store_dir=str(tmp_path))
        tracker.record({
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_creation_input_tokens": 47000,
            "cache_read_input_tokens": 0,
        })

        assert tracker.session_cache_create == 47000
        assert tracker.session_total == 150  # Only input + output count toward total

    def test_default_budget(self, tmp_path):
        tracker = UsageTracker(store_dir=str(tmp_path))
        assert tracker.daily_budget == DEFAULT_DAILY_BUDGET
