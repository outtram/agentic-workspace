"""Single source of truth for project paths — auto-detected from file location."""
from pathlib import Path

# Auto-detect project root from this file's location
# This file lives at: <PROJECT_ROOT>/.claude/reminders/core/paths.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

CLAUDE_DIR = PROJECT_ROOT / ".claude"
WORK_DIR = CLAUDE_DIR / "work"
TASK_DIR = WORK_DIR / "tasks"
TEMPLATE_DIR = CLAUDE_DIR / "templates"
DASHBOARD_DIR = CLAUDE_DIR / "dashboards"
