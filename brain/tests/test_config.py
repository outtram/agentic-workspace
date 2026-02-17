"""Tests for config loading and quiet hours logic."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.core.config import Config


class TestConfig:
    def test_load_from_env(self):
        config = Config.load()
        assert config.db_path  # Not empty
        assert config.memory_dir  # Not empty

    def test_defaults(self):
        config = Config()
        assert config.quiet_start == 22
        assert config.quiet_end == 7
        assert config.heartbeat_interval == 1800


class TestQuietHours:
    def test_midnight_wrap(self):
        """Quiet hours 22-7 wraps midnight."""
        config = Config(quiet_start=22, quiet_end=7)

        assert config.is_quiet_hours(hour=23) is True   # 11pm — quiet
        assert config.is_quiet_hours(hour=3) is True     # 3am — quiet
        assert config.is_quiet_hours(hour=0) is True     # midnight — quiet
        assert config.is_quiet_hours(hour=6) is True     # 6am — quiet
        assert config.is_quiet_hours(hour=7) is False    # 7am — not quiet
        assert config.is_quiet_hours(hour=10) is False   # 10am — not quiet
        assert config.is_quiet_hours(hour=21) is False   # 9pm — not quiet
        assert config.is_quiet_hours(hour=22) is True    # 10pm — quiet
