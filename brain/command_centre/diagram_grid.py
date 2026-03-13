"""Diagram grid widget — renders architecture diagram nodes in a dynamic grid."""
import json
from pathlib import Path

from textual.containers import Container
from textual.widgets import Static

from . import PROJECT_ROOT

DIAGRAMS_DIR = PROJECT_ROOT / ".claude" / "diagrams"

_STATUS_COLOURS = {
    "live": "#00D4AA",
    "in-progress": "#FFD700",
    "planned": "#777777",
    "deprecated": "#FF4444",
}

_MAX_TILES = 20  # generous max for pre-created tiles


def list_diagrams() -> list[Path]:
    """Return all .json diagram files from the diagrams directory."""
    if not DIAGRAMS_DIR.exists():
        return []
    return sorted(DIAGRAMS_DIR.glob("*.json"))


def load_diagram(path: Path) -> dict:
    """Load and return a diagram JSON file."""
    with open(path) as f:
        return json.load(f)


class DiagramGrid(Container):
    """A dynamic-size grid of diagram nodes with drill-down navigation."""

    DEFAULT_CSS = """
    DiagramGrid {
        padding: 0;
        overflow: hidden;
    }
    #diagram-breadcrumb {
        height: 1;
        padding: 0 2;
        background: #111111;
        display: none;
    }
    #diagram-tile-area {
        layout: grid;
        grid-size: 4 3;
        grid-gutter: 1;
        padding: 1;
        height: 1fr;
    }
    .dtile {
        border: solid #333333;
        padding: 0 1;
        max-height: 12;
        overflow: hidden;
    }
    .dtile.has-children {
        border: solid #444444;
    }
    .dtile.focused {
        border: solid #FF6B35;
        background: #2a2a2a;
    }
    .dtile.empty {
        border: solid #1a1a1a;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._diagram: dict | None = None
        self._diagram_path: Path | None = None
        self._layer_stack: list[str] = ["overview"]
        self._focus_index: int = 0
        self._visible_nodes: list[dict] = []
        self._grid_cols: int = 4
        self._grid_rows: int = 3

    def compose(self):
        yield Static(id="diagram-breadcrumb")
        with Container(id="diagram-tile-area"):
            for i in range(_MAX_TILES):
                yield Static(id=f"dtile-{i}", classes="dtile empty")

    # --- Properties ---

    @property
    def current_layer(self) -> str:
        return self._layer_stack[-1] if self._layer_stack else "overview"

    @property
    def focus_index(self) -> int:
        return self._focus_index

    @focus_index.setter
    def focus_index(self, value: int):
        self._focus_index = max(0, min(value, len(self._visible_nodes) - 1))

    @property
    def visible_nodes(self) -> list[dict]:
        return self._visible_nodes

    @property
    def focused_node(self) -> dict | None:
        if 0 <= self._focus_index < len(self._visible_nodes):
            return self._visible_nodes[self._focus_index]
        return None

    @property
    def diagram_title(self) -> str:
        if self._diagram:
            return self._diagram.get("meta", {}).get("title", "Untitled")
        return ""

    @property
    def layer_depth(self) -> int:
        return len(self._layer_stack) - 1

    @property
    def grid_cols(self) -> int:
        return self._grid_cols

    # --- Actions ---

    def load(self, path: Path) -> None:
        """Load a diagram JSON and render the overview layer."""
        self._diagram = load_diagram(path)
        self._diagram_path = path
        self._layer_stack = ["overview"]
        self._focus_index = 0

        meta = self._diagram.get("meta", {})
        self._grid_cols = meta.get("gridCols", 4)
        self._grid_rows = meta.get("gridRows", 3)

        try:
            area = self.query_one("#diagram-tile-area", Container)
            area.styles.grid_size_columns = self._grid_cols
            area.styles.grid_size_rows = self._grid_rows
        except Exception:
            pass

        self._render_layer()

    def drill_in(self) -> bool:
        """Drill into focused node's children. Returns True if drilled."""
        node = self.focused_node
        if not node or not node.get("children"):
            return False
        node_id = node["id"]
        layers = self._diagram.get("layers", {})
        if node_id not in layers:
            return False
        self._layer_stack.append(node_id)
        self._focus_index = 0
        self._render_layer()
        return True

    def zoom_out(self) -> bool:
        """Zoom out one layer. Returns True if zoomed, False if at root."""
        if len(self._layer_stack) <= 1:
            return False
        self._layer_stack.pop()
        self._focus_index = 0
        self._render_layer()
        return True

    # --- Rendering ---

    def _render_layer(self) -> None:
        """Re-render all tiles for the current layer."""
        if not self._diagram:
            return

        layer_id = self.current_layer
        layers = self._diagram.get("layers", {})
        layer = layers.get(layer_id, {})
        visible_ids = set(layer.get("visible", []))

        all_nodes = self._diagram.get("nodes", [])
        self._visible_nodes = [n for n in all_nodes if n["id"] in visible_ids]

        # Sort by grid position (row-major)
        self._visible_nodes.sort(
            key=lambda n: (
                n.get("gridPos", {}).get("row", 0),
                n.get("gridPos", {}).get("col", 0),
            )
        )

        # Adjust grid size for this layer's actual bounds
        if self._visible_nodes:
            max_col = max(
                n.get("gridPos", {}).get("col", 0)
                + n.get("gridPos", {}).get("colSpan", 1)
                for n in self._visible_nodes
            )
            max_row = max(
                n.get("gridPos", {}).get("row", 0)
                + n.get("gridPos", {}).get("rowSpan", 1)
                for n in self._visible_nodes
            )
            self._grid_cols = max(max_col, 1)
            self._grid_rows = max(max_row, 1)
            try:
                area = self.query_one("#diagram-tile-area", Container)
                area.styles.grid_size_columns = self._grid_cols
                area.styles.grid_size_rows = self._grid_rows
            except Exception:
                pass

        self._update_breadcrumb()
        self._update_tiles()

    def _update_tiles(self) -> None:
        """Update tile contents and visibility."""
        max_cells = self._grid_cols * self._grid_rows

        for i in range(_MAX_TILES):
            try:
                tile = self.query_one(f"#dtile-{i}", Static)
            except Exception:
                break

            tile.remove_class("focused", "has-children", "empty")

            if i < len(self._visible_nodes):
                node = self._visible_nodes[i]
                if i == self._focus_index:
                    tile.add_class("focused")
                if node.get("children"):
                    tile.add_class("has-children")
                tile.styles.display = "block"
                tile.update(self._render_node(node))
            elif i < max_cells:
                tile.add_class("empty")
                tile.styles.display = "block"
                tile.update("")
            else:
                tile.styles.display = "none"

    def _render_node(self, node: dict) -> str:
        """Render a single node as Rich markup."""
        label = node.get("label", "Untitled")
        if len(label) > 30:
            label = label[:27] + "..."

        colour = node.get("colour", "#8b949e")
        node_type = node.get("type", "")
        status = node.get("meta", {}).get("status", "")
        children = node.get("children", [])
        owner = node.get("meta", {}).get("owner", "")

        lines = f"[{colour}][bold]{label}[/bold][/]\n"

        if node_type:
            lines += f"[dim]{node_type}[/]\n"

        if status:
            sc = _STATUS_COLOURS.get(status, "#777777")
            lines += f"[{sc}]{status}[/]"

        if children:
            n = len(children)
            lines += f"\n[dim]\u25bc {n} child{'ren' if n != 1 else ''}[/]"

        if owner:
            lines += f"\n[dim]{owner}[/]"

        return lines

    def _update_breadcrumb(self) -> None:
        """Update the breadcrumb bar."""
        try:
            bc = self.query_one("#diagram-breadcrumb", Static)
        except Exception:
            return

        if len(self._layer_stack) <= 1:
            bc.update("")
            bc.styles.display = "none"
            return

        layers = self._diagram.get("layers", {})
        parts = []
        for lid in self._layer_stack:
            layer = layers.get(lid, {})
            title = layer.get("title", lid)
            parts.append(title)

        bc.update(
            f"[dim]\u2190 Esc[/]  [bold #FF6B35]{' \u203a '.join(parts)}[/]"
        )
        bc.styles.display = "block"

    def update_focus(self) -> None:
        """Re-render just the focus state (after arrow key moves)."""
        self._update_tiles()
