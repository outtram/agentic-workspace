"""Brain logger — records every action to brain-log.yml for pattern learning."""
from datetime import datetime
from pathlib import Path

import yaml

from . import PROJECT_ROOT

_LOG_PATH = PROJECT_ROOT / ".claude" / "dashboards" / "brain-log.yml"
_MAX_ENTRIES = 500


def log_action(
    action: str,
    task_ids: list[str] | None = None,
    context: str = "",
    input_text: str = "",
):
    """Append an action to the brain log."""
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "action": action,
    }
    if task_ids:
        entry["task_ids"] = task_ids
    if context:
        entry["context"] = context
    if input_text:
        entry["input"] = input_text

    entries = []
    if _LOG_PATH.exists():
        try:
            data = yaml.safe_load(_LOG_PATH.read_text())
            if isinstance(data, list):
                entries = data
        except yaml.YAMLError:
            pass

    entries.append(entry)

    if len(entries) > _MAX_ENTRIES:
        entries = entries[-_MAX_ENTRIES:]

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LOG_PATH.write_text(yaml.dump(entries, default_flow_style=False, sort_keys=False))
