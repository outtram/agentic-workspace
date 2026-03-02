"""Brain logger — records every action to brain-log.yml for pattern learning."""
import fcntl
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
    """Append an action to the brain log (file-locked to prevent race conditions)."""
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

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(_LOG_PATH, "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.seek(0)
                data = yaml.safe_load(fh.read())
                entries = data if isinstance(data, list) else []

                entries.append(entry)
                if len(entries) > _MAX_ENTRIES:
                    entries = entries[-_MAX_ENTRIES:]

                fh.seek(0)
                fh.truncate()
                fh.write(yaml.dump(entries, default_flow_style=False, sort_keys=False))
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
    except Exception:
        pass
