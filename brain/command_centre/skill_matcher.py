"""Skill/agent matcher — suggests relevant skills and agents based on task content."""

import re
from pathlib import Path

from . import PROJECT_ROOT

# Keyword → agent mapping (agents from .claude/agents/)
_AGENT_SUGGESTIONS = {
    "overseer": {
        "keywords": ["plan", "organise", "prioritise", "review", "triage", "pipeline"],
        "desc": "Orchestrate agents and manage pipeline",
    },
    "work-item-enricher": {
        "keywords": ["vague", "unclear", "improve", "enrich", "flesh out"],
        "desc": "Make tasks more actionable",
    },
    "overdue-wrangler": {
        "keywords": ["overdue", "late", "behind", "backlog", "stale"],
        "desc": "Review overdue tasks and clean backlog",
    },
    "work-tracker": {
        "keywords": ["create", "new task", "track", "add task"],
        "desc": "Create and manage work items",
    },
    "meta-agent": {
        "keywords": ["agent", "skill", "improve", "upgrade", "create agent", "new skill"],
        "desc": "Create/improve agents and skills",
    },
    "dashboard-generator": {
        "keywords": ["dashboard", "eisenhower", "matrix", "visualise"],
        "desc": "Generate Eisenhower dashboard",
    },
    "memory-writer": {
        "keywords": ["remember", "memory", "learn", "note"],
        "desc": "Write to memory system",
    },
}

# Keyword → skill mapping (actionable skills)
_SKILL_SUGGESTIONS = {
    "pptx": {
        "keywords": ["presentation", "slides", "powerpoint", "deck", "pitch", "pptx"],
        "desc": "Create/edit PowerPoint",
    },
    "xlsx": {
        "keywords": ["spreadsheet", "excel", "csv", "data", "numbers", "xlsx"],
        "desc": "Create/edit spreadsheets",
    },
    "docx": {
        "keywords": ["document", "word", "report", "brief", "docx", "letter"],
        "desc": "Create/edit Word docs",
    },
    "pdf": {
        "keywords": ["pdf", "convert pdf", "merge pdf", "extract pdf"],
        "desc": "Read/merge/split PDFs",
    },
    "frontend-design": {
        "keywords": ["website", "landing page", "ui", "frontend", "web", "react", "html"],
        "desc": "Build frontend interfaces",
    },
    "cinematic-landing-page": {
        "keywords": ["landing page", "cinematic", "gsap", "animation"],
        "desc": "Build cinematic landing pages",
    },
    "pptx-arch-diagrams": {
        "keywords": ["architecture", "diagram", "system design", "microservice"],
        "desc": "Architecture diagrams in PPT",
    },
    "confluence-automation": {
        "keywords": ["confluence", "wiki", "documentation"],
        "desc": "Manage Confluence docs",
    },
    "agent-browser": {
        "keywords": ["browse", "scrape", "fetch", "url", "http", "website"],
        "desc": "Browse and interact with websites",
    },
    "humanizer": {
        "keywords": ["ai writing", "rewrite", "natural", "humanise", "humanize"],
        "desc": "Remove AI-sounding writing",
    },
    "doc-coauthoring": {
        "keywords": ["proposal", "spec", "technical spec", "decision doc"],
        "desc": "Co-author documentation",
    },
    "internal-comms": {
        "keywords": ["status report", "newsletter", "internal", "comms", "update"],
        "desc": "Write internal communications",
    },
    "canvas-design": {
        "keywords": ["poster", "art", "design", "visual", "png"],
        "desc": "Create visual art/posters",
    },
    "theme-factory": {
        "keywords": ["theme", "brand", "style", "colour scheme"],
        "desc": "Apply themes to artifacts",
    },
}


def match_for_task(task: dict) -> dict:
    """Return suggested agents and skills for a task.

    Returns {"agents": [...], "skills": [...]} where each item is
    {"name": str, "desc": str, "score": int}.
    """
    title = task.get("title", "").lower()
    desc = task.get("_description", "").lower()
    text = f"{title} {desc}"

    # Check for URLs
    has_url = bool(re.search(r"https?://", text))

    agents = []
    for name, info in _AGENT_SUGGESTIONS.items():
        score = sum(1 for kw in info["keywords"] if kw in text)
        if score > 0:
            agents.append({"name": name, "desc": info["desc"], "score": score})

    skills = []
    for name, info in _SKILL_SUGGESTIONS.items():
        score = sum(1 for kw in info["keywords"] if kw in text)
        if name == "agent-browser" and has_url:
            score += 2
        if score > 0:
            skills.append({"name": name, "desc": info["desc"], "score": score})

    # Sort by score descending, take top 3
    agents.sort(key=lambda x: x["score"], reverse=True)
    skills.sort(key=lambda x: x["score"], reverse=True)

    return {
        "agents": agents[:3],
        "skills": skills[:3],
    }
