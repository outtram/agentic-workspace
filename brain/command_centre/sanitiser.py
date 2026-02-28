"""Client name sanitisation — cross-cutting concern for all display output."""
import re
from pathlib import Path

import yaml

from . import PROJECT_ROOT

_RULES_PATH = PROJECT_ROOT / ".claude" / "scripts" / "sanitise_rules.yml"
_rules_cache: list[dict] | None = None


def load_rules() -> list[dict]:
    """Load sanitisation rules from YAML (cached after first call)."""
    global _rules_cache
    if _rules_cache is None:
        if _RULES_PATH.exists():
            data = yaml.safe_load(_RULES_PATH.read_text())
            _rules_cache = data.get("replacements", [])
        else:
            _rules_cache = []
    return _rules_cache


def sanitise(text: str) -> str:
    """Apply all sanitisation rules to text."""
    if not text:
        return text
    for rule in load_rules():
        flags = re.IGNORECASE if rule.get("case_insensitive", True) else 0
        text = re.sub(rule["pattern"], rule["replacement"], text, flags=flags)
    return text
