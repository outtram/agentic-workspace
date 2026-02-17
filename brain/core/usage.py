"""Track token usage across OutBot sessions with daily persistence."""

import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

# Default estimated daily token budget (Max 5x: ~88k per 5h window × 3 windows)
# Override with OUTBOT_DAILY_TOKEN_BUDGET env var
DEFAULT_DAILY_BUDGET = 264_000


class UsageTracker:
    """Accumulates token usage per session and persists daily totals."""

    def __init__(
        self,
        store_dir: str = "brain/store/usage",
        daily_budget: int = DEFAULT_DAILY_BUDGET,
    ):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.daily_budget = daily_budget

        # Session counters
        self.session_input = 0
        self.session_output = 0
        self.session_cache_create = 0
        self.session_cache_read = 0
        self.session_cost_usd = 0.0
        self.session_calls = 0

        # Load today's running total
        self._today = date.today().isoformat()
        self._daily_file = self.store_dir / f"{self._today}.json"
        self._daily = self._load_daily()

    def record(self, usage: dict, cost_usd: float = 0.0):
        """Record usage from a single Claude CLI call.

        Args:
            usage: The 'usage' dict from Claude JSON output
            cost_usd: The total_cost_usd from Claude JSON output
        """
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cache_create = usage.get("cache_creation_input_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)

        # Session totals
        self.session_input += input_tokens
        self.session_output += output_tokens
        self.session_cache_create += cache_create
        self.session_cache_read += cache_read
        self.session_cost_usd += cost_usd
        self.session_calls += 1

        # Daily totals
        self._check_date_rollover()
        self._daily["input_tokens"] += input_tokens
        self._daily["output_tokens"] += output_tokens
        self._daily["cache_creation"] += cache_create
        self._daily["cache_read"] += cache_read
        self._daily["cost_usd"] += cost_usd
        self._daily["calls"] += 1

        self._save_daily()

    @property
    def session_total(self) -> int:
        """Total tokens used this session (input + output)."""
        return self.session_input + self.session_output

    @property
    def daily_total(self) -> int:
        """Total tokens used today (input + output)."""
        self._check_date_rollover()
        return self._daily["input_tokens"] + self._daily["output_tokens"]

    @property
    def daily_percent(self) -> float:
        """Estimated percentage of daily budget used."""
        if self.daily_budget <= 0:
            return 0.0
        return min((self.daily_total / self.daily_budget) * 100, 100.0)

    def format_status(self) -> str:
        """Format a compact status line for display in the terminal."""
        session_k = self.session_total / 1000
        daily_k = self.daily_total / 1000
        budget_k = self.daily_budget / 1000
        pct = self.daily_percent
        return f"session: {session_k:.1f}k | today: {daily_k:.0f}k/{budget_k:.0f}k | {pct:.0f}%"

    def format_session_summary(self) -> str:
        """Format a summary for end-of-session display."""
        lines = []
        lines.append(f"  Tokens this session: {self.session_total:,} ({self.session_calls} calls)")
        lines.append(f"  Tokens today (OutBot): {self.daily_total:,} / ~{self.daily_budget:,} est. budget")

        pct = self.daily_percent
        bar_width = 20
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        lines.append(f"  [{bar}] {pct:.0f}%")

        if self.session_cost_usd > 0:
            lines.append(f"  Est. cost: ${self.session_cost_usd:.3f}")

        return "\n".join(lines)

    def _check_date_rollover(self):
        """Reset daily counters if the date has changed."""
        today = date.today().isoformat()
        if today != self._today:
            self._today = today
            self._daily_file = self.store_dir / f"{self._today}.json"
            self._daily = self._load_daily()

    def _load_daily(self) -> dict:
        """Load today's usage file or return fresh counters."""
        if self._daily_file.exists():
            try:
                return json.loads(self._daily_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, KeyError):
                pass

        return {
            "date": self._today,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation": 0,
            "cache_read": 0,
            "cost_usd": 0.0,
            "calls": 0,
        }

    def _save_daily(self):
        """Persist today's usage to disk."""
        self._daily_file.write_text(
            json.dumps(self._daily, indent=2) + "\n",
            encoding="utf-8",
        )
