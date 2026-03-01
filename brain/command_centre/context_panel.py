"""Right-side context panel — today shortlist + detail/response."""
from textual.containers import VerticalScroll
from textual.widgets import Static

from .sanitiser import sanitise
from .skill_matcher import match_for_task
from .task_loader import QUADRANT_COLOURS, QUADRANT_LABELS


class ContextPanel(VerticalScroll):
    """Shows today shortlist, task detail, and OutBot responses."""

    DEFAULT_CSS = """
    ContextPanel {
        width: 1fr;
        min-width: 28;
        border-left: solid #333333;
        padding: 1 2;
    }
    #panel-content {
        width: 100%;
    }
    """

    def compose(self):
        yield Static(id="panel-content")

    def update_content(
        self,
        today_ids: list[str],
        all_tasks: list[dict],
        focused_task: dict | None = None,
        response: str = "",
    ):
        """Refresh panel content."""
        content = self._render_today(today_ids, all_tasks)
        if response:
            content += "\n" + self._render_response(response)
        elif focused_task:
            content += "\n" + self._render_detail(focused_task, all_tasks)
        try:
            self.query_one("#panel-content", Static).update(content)
        except Exception:
            pass

    def _render_today(self, today_ids: list[str], all_tasks: list[dict]) -> str:
        """Render the today shortlist."""
        count = len(today_ids)
        lines = f"[bold #00D4AA]TODAY[/] [dim]({count} task{'s' if count != 1 else ''})[/]\n"
        lines += "[#333333]" + "\u2501" * 24 + "[/]\n"

        if not today_ids:
            lines += "[dim](none yet)[/]\n"
            lines += "[dim]Press t to add tasks[/]\n"
        else:
            task_map = {t["id"]: t for t in all_tasks if "id" in t}
            for tid in today_ids:
                t = task_map.get(tid)
                if t:
                    q = t.get("eisenhower_quadrant", "q4")
                    colour = QUADRANT_COLOURS.get(q, "#3D3D3D")
                    name = sanitise(t.get("title", tid)).replace("[", r"\[")
                    if len(name) > 24:
                        name = name[:21] + "..."
                    lines += f"[{colour}]\u25cf[/] {name}\n"
                else:
                    lines += f"[dim]\u25cb {tid}[/]\n"

        return lines

    def _render_response(self, response: str) -> str:
        """Render OutBot response."""
        lines = "\n[bold #FF6B35]OUTBOT[/]\n"
        lines += "[#333333]" + "\u2501" * 24 + "[/]\n"
        lines += response
        return lines

    def _render_detail(self, task: dict, all_tasks: list[dict] | None = None) -> str:
        """Render focused task detail."""
        lines = "\n[bold]DETAIL[/]\n"
        lines += "[#333333]" + "\u2501" * 24 + "[/]\n"

        title = sanitise(task.get("title", "Untitled")).replace("[", r"\[")
        out_id = task.get("id", "???")
        q = task.get("eisenhower_quadrant", "q4")
        colour = QUADRANT_COLOURS.get(q, "#3D3D3D")
        label = QUADRANT_LABELS.get(q, "Q4")

        lines += f"[{colour}]{label}[/]\n"
        lines += f"[bold]{title}[/]\n"
        lines += f"[dim]{out_id}[/]\n"

        if "_due_date" in task:
            due_str = task["_due_date"].strftime("%d %b %Y")
            if task.get("_overdue"):
                lines += f"[bold red]OVERDUE: {due_str}[/]\n"
            else:
                lines += f"[dim]Due: {due_str}[/]\n"

        priority = task.get("priority", "low")
        if priority != "low":
            lines += f"[dim]Priority: {priority}[/]\n"

        parent = task.get("parent")
        if parent:
            parent_title = ""
            if all_tasks:
                for t in all_tasks:
                    if t.get("id") == parent:
                        parent_title = sanitise(
                            t.get("title", "")
                        ).replace("[", r"\[")
                        break
            if parent_title:
                lines += f"[dim]\u2191 Parent: {parent} — {parent_title}[/]\n"
            else:
                lines += f"[dim]\u2191 Parent: {parent}[/]\n"

        children = task.get("children", [])
        if children:
            lines += f"[dim]\u25bc {len(children)} subtask{'s' if len(children) != 1 else ''}:[/]\n"
            for child_id in children[:5]:
                child_title = ""
                if all_tasks:
                    for t in all_tasks:
                        if t.get("id") == child_id:
                            child_title = sanitise(
                                t.get("title", "")
                            ).replace("[", r"\[")
                            break
                if child_title:
                    lines += f"  [dim]{child_id}: {child_title[:30]}[/]\n"
                else:
                    lines += f"  [dim]{child_id}[/]\n"
            if len(children) > 5:
                lines += f"  [dim]... +{len(children) - 5} more[/]\n"

        desc = sanitise(task.get("_description", "")).replace("[", r"\[")
        if desc:
            lines += f"\n{desc[:300]}\n"
            if len(desc) > 300:
                lines += "[dim]...[/]\n"

        # Actions hint
        lines += "\n[bold]ACTIONS[/]\n"
        lines += "[#333333]" + "\u2501" * 24 + "[/]\n"
        lines += "[dim]/enrich  /research  /done[/]\n"
        lines += "[dim]e Edit  t Today  [bold #FF6B35]x Actions[/][/]\n"

        # Contextual suggestions
        suggestions = match_for_task(task)
        if suggestions["agents"] or suggestions["skills"]:
            lines += "\n[bold]Suggested[/]\n"
            for a in suggestions["agents"][:2]:
                lines += f"[#00D4AA]{a['name']}[/] [dim]{a['desc']}[/]\n"
            for s in suggestions["skills"][:2]:
                lines += f"[#00D4AA]{s['name']}[/] [dim]{s['desc']}[/]\n"

        return lines
