"""3x3 tile grid widget for the Command Centre."""
from textual.containers import Container
from textual.widgets import Static

from .config_loader import load_config
from .sanitiser import sanitise
from .task_loader import QUADRANT_COLOURS, QUADRANT_LABELS


class TileGrid(Container):
    """A 3x3 grid of task tiles with navigation and selection."""

    DEFAULT_CSS = """
    TileGrid {
        layout: grid;
        grid-size: 3 3;
        grid-gutter: 1;
        padding: 1;
    }
    .tile {
        border: solid #333333;
        padding: 0 1;
        height: 100%;
    }
    .tile.focused {
        border: solid #FF6B35;
        background: #2a2a2a;
    }
    .tile.selected {
        border: double #00D4AA;
    }
    .tile.focused.selected {
        border: double #FF6B35;
        background: #2a2a2a;
    }
    .tile.empty {
        border: solid #1a1a1a;
    }
    """

    def compose(self):
        for i in range(9):
            yield Static(id=f"tile-{i}", classes="tile empty")

    def update_tiles(
        self,
        tasks: list[dict],
        focus_index: int,
        selected_ids: set[str],
        today_ids: list[str],
    ):
        """Re-render all 9 tiles with current state."""
        colours = load_config()["display"]

        for i in range(9):
            tile = self.query_one(f"#tile-{i}", Static)
            tile.remove_class("focused", "selected", "empty")

            if i < len(tasks):
                task = tasks[i]
                tid = task.get("id", "")

                if i == focus_index:
                    tile.add_class("focused")
                if tid in selected_ids:
                    tile.add_class("selected")

                tile.update(
                    self._render_tile(
                        task,
                        tid in selected_ids,
                        tid in today_ids,
                        colours,
                    )
                )
            else:
                tile.add_class("empty")
                tile.update("")

    def _render_tile(
        self, task: dict, is_selected: bool, is_today: bool, colours: dict
    ) -> str:
        """Render a single tile's content as Rich markup."""
        title = sanitise(task.get("title", "Untitled")).replace("[", r"\[")
        if len(title) > 38:
            title = title[:35] + "..."

        q = task.get("eisenhower_quadrant", "q4")
        out_id = task.get("id", "???")

        colour = QUADRANT_COLOURS.get(q, "#3D3D3D")
        label = QUADRANT_LABELS.get(q, "Q4")

        # Indicators
        indicators = ""
        if is_selected:
            indicators += "[#00D4AA]\u2713[/] "
        if is_today:
            indicators += "[green]\u25cf[/] "
        if task.get("_overdue"):
            indicators += "[bold red]![/] "
        elif task.get("_due_today"):
            indicators += "[bold yellow]\u25b2[/] "

        lines = f"{indicators}[{colour}]{label}[/]\n"
        lines += f"[bold]{title}[/]\n"
        lines += f"[dim]{out_id}[/]"

        if "_due_date" in task:
            lines += f" [dim]\u00b7 {task['_due_date'].strftime('%d %b')}[/]"

        priority = task.get("priority", "")
        if priority and priority != "low":
            lines += f" [dim]\u00b7 {priority}[/]"

        return lines
