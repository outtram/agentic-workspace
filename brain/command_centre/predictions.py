"""Prediction engine — suggests today list based on brain-log patterns."""

from collections import Counter
from datetime import datetime, date, timedelta

import yaml

from . import PROJECT_ROOT

_LOG_FILE = PROJECT_ROOT / ".claude" / "dashboards" / "brain-log.yml"
_PRED_FILE = PROJECT_ROOT / ".claude" / "dashboards" / "predictions.yml"


def generate_predictions(
    all_tasks: list[dict], today_ids: list[str]
) -> list[dict]:
    """Analyse brain-log and return predicted today suggestions."""
    log = _load_log()
    if not log:
        return []

    active_ids = {t["id"] for t in all_tasks if "id" in t}
    already_today = set(today_ids)

    scores: Counter = Counter()

    _score_frequency(log, scores)
    _score_day_of_week(log, scores)
    _score_incomplete_yesterday(log, scores)

    # Filter to active tasks not already in today
    candidates = [
        (tid, score)
        for tid, score in scores.most_common(10)
        if tid in active_ids and tid not in already_today
    ]

    if not candidates:
        return []

    # Take top 3-5 suggestions (need score > 1 to avoid noise)
    suggestions = [(tid, s) for tid, s in candidates[:5] if s > 1]
    if not suggestions:
        return []

    task_map = {t["id"]: t for t in all_tasks if "id" in t}
    result = []
    for tid, score in suggestions:
        task = task_map.get(tid, {})
        result.append(
            {
                "id": tid,
                "title": task.get("title", tid),
                "score": score,
            }
        )

    _save_predictions(result)
    return result


def _load_log() -> list[dict]:
    if not _LOG_FILE.exists():
        return []
    try:
        data = yaml.safe_load(_LOG_FILE.read_text())
        return data if isinstance(data, list) else []
    except yaml.YAMLError:
        return []


def _score_frequency(log: list[dict], scores: Counter):
    """Score tasks by how often they're selected or added to today."""
    for entry in log:
        action = entry.get("action", "")
        if action in ("selected", "added_to_today"):
            for tid in entry.get("task_ids", []):
                scores[tid] += 1


def _score_day_of_week(log: list[dict], scores: Counter):
    """Boost tasks that tend to be selected on this day of week."""
    today_dow = date.today().weekday()
    for entry in log:
        ts = entry.get("timestamp", "")
        try:
            entry_dow = datetime.fromisoformat(ts).weekday()
        except (ValueError, TypeError):
            continue
        if entry_dow == today_dow:
            action = entry.get("action", "")
            if action in ("selected", "added_to_today"):
                for tid in entry.get("task_ids", []):
                    scores[tid] += 2


def _score_incomplete_yesterday(log: list[dict], scores: Counter):
    """Boost tasks selected yesterday but not completed."""
    yesterday = date.today() - timedelta(days=1)
    selected_yesterday: set[str] = set()
    completed_yesterday: set[str] = set()

    for entry in log:
        ts = entry.get("timestamp", "")
        try:
            entry_date = datetime.fromisoformat(ts).date()
        except (ValueError, TypeError):
            continue
        if entry_date != yesterday:
            continue

        action = entry.get("action", "")
        tids = entry.get("task_ids", [])

        if action in ("selected", "added_to_today"):
            selected_yesterday.update(tids)
        elif action == "done":
            completed_yesterday.update(tids)

    for tid in selected_yesterday - completed_yesterday:
        scores[tid] += 3  # Heaviest weight — unfinished business


def _save_predictions(suggestions: list[dict]):
    """Save predictions to YAML."""
    _PRED_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "date": date.today().isoformat(),
        "generated": datetime.now().isoformat(),
        "suggestions": suggestions,
    }
    _PRED_FILE.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False)
    )
