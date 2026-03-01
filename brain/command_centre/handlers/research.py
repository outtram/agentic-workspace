"""Research handler — /research fetches URLs and summarises findings."""

import re

from .. import PROJECT_ROOT
from ..brain_logger import log_action

_TASK_DIR = PROJECT_ROOT / ".claude" / "work" / "tasks"
_URL_PATTERN = re.compile(r"https?://[^\s<>\"{}|\\^`\[\]]+")


async def handle_research(task_ids, all_tasks, claude, progress=None):
    """Research selected tasks — fetch URLs or use Claude for topics."""
    if not task_ids:
        return "No tasks selected"

    task_map = {t["id"]: t for t in all_tasks if "id" in t}
    researched = 0

    for tid in task_ids:
        task = task_map.get(tid)
        if not task:
            continue

        title = task.get("title", "")
        desc = task.get("_description", "")
        text = f"{title} {desc}"

        urls = _URL_PATTERN.findall(text)

        if urls:
            if progress:
                await progress(f"[dim]Fetching {urls[0][:40]}...[/]")
            findings = await _research_url(urls[0], claude)
        else:
            if progress:
                await progress(f"[dim]Researching: {title[:30]}...[/]")
            findings = await _research_topic(title, desc, claude)

        if findings:
            _append_findings(tid, findings)
            researched += 1

    log_action("researched", task_ids=task_ids)
    return f"Researched {researched} task{'s' if researched != 1 else ''}"


async def _research_url(url, claude):
    """Fetch URL and summarise content via Claude."""
    content = ""
    try:
        import httpx

        async with httpx.AsyncClient(
            timeout=15, follow_redirects=True
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            # Take first 10k chars of response
            content = resp.text[:10000]
    except Exception as e:
        content = f"(Failed to fetch: {e})"

    prompt = (
        "Summarise this web page content in 3-5 bullet points, "
        "focusing on key facts and actionable information:\n\n"
        f"URL: {url}\n\n{content}"
    )
    try:
        return await claude.ask(prompt)
    except Exception:
        return None


async def _research_topic(title, desc, claude):
    """Use Claude to research a topic when no URL is available."""
    prompt = (
        "Research this task and provide 3-5 actionable findings:\n\n"
        f"Title: {title}\n"
        f"Description: {desc or '(none)'}\n\n"
        "Provide practical findings, relevant facts, and next steps."
    )
    try:
        return await claude.ask(prompt)
    except Exception:
        return None


def _append_findings(task_id, findings):
    """Append research findings to a task's markdown file."""
    task_file = _TASK_DIR / f"{task_id}.md"
    if not task_file.exists():
        return

    content = task_file.read_text()

    if "## Research" in content:
        # Replace existing research section
        parts = content.split("## Research", 1)
        before = parts[0]
        rest_parts = parts[1].split("\n##", 1)
        rest = "\n##" + rest_parts[1] if len(rest_parts) > 1 else ""
        content = f"{before}## Research\n\n{findings}\n{rest}"
    else:
        content = content.rstrip() + f"\n\n## Research\n\n{findings}\n"

    task_file.write_text(content)
