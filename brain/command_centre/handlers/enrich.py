"""Enrich handler — /enrich sends task descriptions to Claude for improvement."""
import yaml

from ..brain_logger import log_action
from ..task_loader import find_task_file


def _update_task_description(task_id: str, new_description: str):
    """Update the description section of a task markdown file."""
    task_file = find_task_file(task_id)
    if not task_file:
        return

    content = task_file.read_text()
    lines = content.split("\n")
    new_lines = []
    in_desc = False
    desc_replaced = False

    for line in lines:
        if line.startswith("## Description"):
            new_lines.append(line)
            new_lines.append("")
            new_lines.append(new_description)
            new_lines.append("")
            in_desc = True
            desc_replaced = True
            continue
        if in_desc:
            if line.startswith("##"):
                in_desc = False
                new_lines.append(line)
            continue
        new_lines.append(line)

    if not desc_replaced:
        new_lines.append("")
        new_lines.append("## Description")
        new_lines.append("")
        new_lines.append(new_description)
        new_lines.append("")

    task_file.write_text("\n".join(new_lines))


async def handle_enrich(task_ids: list[str], all_tasks: list[dict], claude) -> str:
    """Enrich selected task descriptions via Claude."""
    if not task_ids:
        return "No tasks selected"

    task_map = {t["id"]: t for t in all_tasks if "id" in t}
    enriched = 0

    for tid in task_ids:
        task = task_map.get(tid)
        if not task:
            continue

        title = task.get("title", "")
        desc = task.get("_description", "")

        prompt = (
            "Make this task more actionable and clear. "
            "Return 2-3 concise sentences describing what needs to be done, "
            "any key steps, and the definition of done. "
            "Return ONLY the improved description text, nothing else.\n\n"
            f"Title: {title}\n"
            f"Current description: {desc or '(none)'}"
        )

        try:
            improved = await claude.ask(prompt)
            _update_task_description(tid, improved.strip())
            enriched += 1
        except Exception:
            pass

    log_action("enriched", task_ids=task_ids)
    return f"Enriched {enriched} task{'s' if enriched != 1 else ''}"
