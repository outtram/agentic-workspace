"""Load Command Centre configuration from YAML with sensible defaults."""
from pathlib import Path

import yaml

from . import PROJECT_ROOT

_CONFIG_PATH = PROJECT_ROOT / ".claude" / "config" / "command-centre.yml"

_DEFAULTS = {
    "hotkeys": {
        "add_to_today": "t",
        "mark_done": "d",
        "page_left": "[",
        "page_right": "]",
        "select_all": "a",
        "deselect_all": "n",
        "help": "?",
        "command_bar": "/",
        "filter_mode": ":",
    },
    "display": {
        "tiles_per_row": 3,
        "rows": 3,
        "colour_q1": "#FF6B35",
        "colour_q2": "#00D4AA",
        "colour_q3": "#777777",
        "colour_q4": "#3D3D3D",
        "colour_focused": "#FF6B35",
        "colour_selected": "#00D4AA",
    },
    "behaviour": {
        "sanitise_output": True,
    },
}

_cache: dict | None = None


def load_config() -> dict:
    """Load config, merging file values over defaults."""
    global _cache
    if _cache is not None:
        return _cache

    config = {k: dict(v) if isinstance(v, dict) else v for k, v in _DEFAULTS.items()}

    if _CONFIG_PATH.exists():
        try:
            file_data = yaml.safe_load(_CONFIG_PATH.read_text())
            if isinstance(file_data, dict):
                for section, values in file_data.items():
                    if section in config and isinstance(values, dict):
                        config[section] = {**config[section], **values}
                    else:
                        config[section] = values
        except yaml.YAMLError:
            pass

    _cache = config
    return config
