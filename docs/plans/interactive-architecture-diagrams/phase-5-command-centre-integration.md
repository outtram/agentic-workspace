# Phase 5: Command Centre Integration

## Goal

Integrate the diagram viewer as a mode within Command Centre, allowing seamless switching between task management and architecture diagrams.

## Prerequisites

- Phases 1-4 complete
- Command Centre running and stable
- Diagram viewer validated with real diagrams

## Deliverables

- [ ] New `/diagram` command to switch to diagram mode
- [ ] Load diagrams from `.claude/diagrams/` folder
- [ ] Same hotkeys work in both task grid and diagram mode
- [ ] Diagram nodes can link to tasks
- [ ] Context panel shows node details
- [ ] Status bar shows diagram info

---

## Architecture

### Mode System

Command Centre will have two primary modes:

```
┌─────────────────────────────────────────────────────────────┐
│                    COMMAND CENTRE                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  MODE SWITCHER                       │   │
│  │   [Tasks]  [Diagrams]  [Calendar]  [Memory]         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │              ACTIVE MODE CONTENT                      │   │
│  │                                                       │   │
│  │   (Tile Grid OR Diagram Grid OR Calendar View)       │   │
│  │                                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ⌘ COMMAND BAR                                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
brain/command_centre/
├── app.py                    # Main app (mode switching)
├── modes/
│   ├── __init__.py
│   ├── tasks.py              # Existing tile grid (refactored)
│   └── diagrams.py           # NEW: Diagram mode
├── widgets/
│   ├── tile_grid.py          # Existing
│   ├── diagram_grid.py       # NEW: Diagram rendering
│   └── diagram_connections.py # NEW: SVG connections
└── handlers/
    └── diagram.py            # NEW: Diagram commands

.claude/diagrams/
├── program-capabilities.json
├── system-architecture.json
└── customer-journey.json
```

---

## Technical Specification

### Diagram Mode Widget (Textual)

```python
# brain/command_centre/modes/diagrams.py

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Label
from textual.binding import Binding
from pathlib import Path
import json

class DiagramMode(Container):
    """Diagram viewer mode for Command Centre."""
    
    BINDINGS = [
        Binding("enter", "drill_in", "Drill In"),
        Binding("escape", "zoom_out", "Zoom Out"),
        Binding("backspace", "zoom_out", "Zoom Out"),
        Binding("space", "toggle_select", "Select"),
        Binding("c", "connect", "Connect"),
        Binding("e", "edit", "Edit"),
        Binding("n", "new_node", "New Node"),
        Binding("x", "delete", "Delete"),
    ]
    
    def __init__(self, diagram_path: Path = None):
        super().__init__()
        self.diagram_path = diagram_path
        self.diagram_data = None
        self.current_layer = "overview"
        self.layer_stack = ["overview"]
        self.focused_index = 0
        self.selected_nodes = set()
        
    def compose(self) -> ComposeResult:
        yield DiagramBreadcrumb(id="diagram-breadcrumb")
        yield DiagramGrid(id="diagram-grid")
        yield DiagramConnections(id="diagram-connections")
        
    def on_mount(self):
        if self.diagram_path:
            self.load_diagram(self.diagram_path)
        else:
            self.show_diagram_picker()
            
    def load_diagram(self, path: Path):
        """Load diagram from JSON file."""
        with open(path) as f:
            self.diagram_data = json.load(f)
        self.current_layer = "overview"
        self.layer_stack = ["overview"]
        self.render_layer()
        self.update_breadcrumb()
        
    def render_layer(self):
        """Render current layer's nodes and connections."""
        grid = self.query_one("#diagram-grid", DiagramGrid)
        connections = self.query_one("#diagram-connections", DiagramConnections)
        
        layer = self.diagram_data["layers"].get(self.current_layer, {})
        visible_ids = layer.get("visible", [])
        
        nodes = [
            n for n in self.diagram_data["nodes"]
            if n["id"] in visible_ids
        ]
        
        visible_connections = [
            c for c in self.diagram_data["connections"]
            if c["from"] in visible_ids and c["to"] in visible_ids
        ]
        
        grid.render_nodes(nodes, self.diagram_data["meta"])
        connections.render_connections(visible_connections, nodes)
        
    def action_drill_in(self):
        """Drill into focused node."""
        focused_node = self.get_focused_node()
        if focused_node and focused_node.get("children"):
            self.layer_stack.append(focused_node["id"])
            self.current_layer = focused_node["id"]
            self.focused_index = 0
            self.render_layer()
            self.update_breadcrumb()
            
    def action_zoom_out(self):
        """Zoom out one layer."""
        if len(self.layer_stack) > 1:
            self.layer_stack.pop()
            self.current_layer = self.layer_stack[-1]
            self.focused_index = 0
            self.render_layer()
            self.update_breadcrumb()
            
    def show_diagram_picker(self):
        """Show list of available diagrams."""
        diagrams_dir = Path(".claude/diagrams")
        if diagrams_dir.exists():
            diagrams = list(diagrams_dir.glob("*.json"))
            # Show picker in context panel
            self.app.show_diagram_list(diagrams)
```

### Diagram Grid Widget

```python
# brain/command_centre/widgets/diagram_grid.py

from textual.widgets import Static
from textual.containers import Grid
from rich.text import Text
from rich.panel import Panel
from rich.style import Style

class DiagramGrid(Grid):
    """Grid of diagram nodes."""
    
    DEFAULT_CSS = """
    DiagramGrid {
        grid-size: 6 4;
        grid-gutter: 1;
        padding: 1;
    }
    """
    
    def render_nodes(self, nodes: list, meta: dict):
        """Render nodes in grid."""
        self.remove_children()
        
        # Update grid size from meta
        cols = meta.get("gridCols", 6)
        rows = meta.get("gridRows", 4)
        self.styles.grid_size_columns = cols
        self.styles.grid_size_rows = rows
        
        for node in nodes:
            widget = DiagramNode(node)
            col = node["gridPos"]["col"]
            row = node["gridPos"]["row"]
            col_span = node["gridPos"].get("colSpan", 1)
            row_span = node["gridPos"].get("rowSpan", 1)
            
            widget.styles.column_span = col_span
            widget.styles.row_span = row_span
            
            self.mount(widget)


class DiagramNode(Static):
    """Single diagram node."""
    
    DEFAULT_CSS = """
    DiagramNode {
        border: solid $secondary;
        padding: 1;
        text-align: center;
    }
    
    DiagramNode:focus {
        border: solid $accent;
    }
    
    DiagramNode.selected {
        border: solid $success;
        background: $success 10%;
    }
    
    DiagramNode.has-children::after {
        content: "▼";
    }
    """
    
    def __init__(self, node_data: dict):
        super().__init__()
        self.node_data = node_data
        self.can_focus = True
        
    def render(self) -> Text:
        icon = self.node_data.get("icon", "")
        label = self.node_data["label"]
        status = self.node_data.get("meta", {}).get("status", "")
        
        text = Text()
        if icon:
            text.append(f"[{icon}]\n", style="dim")
        text.append(label, style="bold")
        if status:
            colour = "green" if status == "live" else "yellow" if status == "in-progress" else "dim"
            text.append(f"\n{status}", style=colour)
            
        return text
```

### Router Integration

```python
# brain/command_centre/handlers/diagram.py

from pathlib import Path

async def handle_diagram_command(app, args: str):
    """Handle /diagram commands."""
    
    if not args:
        # Show diagram picker
        app.switch_to_diagram_mode()
        return
        
    # Check if it's a diagram name
    diagram_path = Path(f".claude/diagrams/{args}.json")
    if diagram_path.exists():
        app.switch_to_diagram_mode(diagram_path)
        return
        
    # Check subcommands
    parts = args.split()
    cmd = parts[0]
    
    if cmd == "list":
        diagrams = list(Path(".claude/diagrams").glob("*.json"))
        return "\n".join(d.stem for d in diagrams)
        
    elif cmd == "new":
        name = parts[1] if len(parts) > 1 else "untitled"
        return await create_new_diagram(name)
        
    elif cmd == "export":
        format = parts[1] if len(parts) > 1 else "png"
        return await export_current_diagram(app, format)
        
    return f"Unknown diagram command: {cmd}"


async def create_new_diagram(name: str) -> str:
    """Create a new empty diagram."""
    template = {
        "meta": {
            "title": name.replace("-", " ").title(),
            "gridMode": "strict",
            "gridCols": 6,
            "gridRows": 4
        },
        "nodes": [],
        "connections": [],
        "layers": {
            "overview": {
                "title": "Overview",
                "visible": []
            }
        }
    }
    
    path = Path(f".claude/diagrams/{name}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w") as f:
        json.dump(template, f, indent=2)
        
    return f"Created: {path}"
```

### App Mode Switching

```python
# brain/command_centre/app.py (additions)

from .modes.diagrams import DiagramMode
from .modes.tasks import TaskMode

class CommandCentreApp(App):
    
    MODES = {
        "tasks": TaskMode,
        "diagrams": DiagramMode,
    }
    
    def __init__(self):
        super().__init__()
        self.current_mode = "tasks"
        
    def switch_mode(self, mode: str, **kwargs):
        """Switch between modes."""
        if mode not in self.MODES:
            return
            
        # Remove current mode widget
        current = self.query_one("#mode-content")
        current.remove()
        
        # Mount new mode
        mode_class = self.MODES[mode]
        new_mode = mode_class(**kwargs)
        self.mount(new_mode, before="#command-bar")
        
        self.current_mode = mode
        self.update_status_bar()
        
    def switch_to_diagram_mode(self, diagram_path: Path = None):
        """Switch to diagram mode."""
        self.switch_mode("diagrams", diagram_path=diagram_path)
        
    def switch_to_task_mode(self):
        """Switch to task mode."""
        self.switch_mode("tasks")
```

### Linking Nodes to Tasks

Diagram nodes can reference tasks via their `meta` field:

```json
{
    "id": "cap-kyc",
    "label": "KYC Verification",
    "meta": {
        "task_id": "OUT-256",
        "status": "in-progress"
    }
}
```

When a node with `task_id` is focused, the context panel shows the linked task details:

```python
def on_node_focus(self, node_data: dict):
    """Handle node focus - show details in context panel."""
    task_id = node_data.get("meta", {}).get("task_id")
    
    if task_id:
        # Load and display linked task
        task = self.app.task_loader.get_task(task_id)
        self.app.context_panel.show_task(task)
    else:
        # Show node details
        self.app.context_panel.show_node(node_data)
```

---

## Slash Commands

| Command | Action |
|---------|--------|
| `/diagram` | Switch to diagram mode, show picker |
| `/diagram [name]` | Open specific diagram |
| `/diagram list` | List available diagrams |
| `/diagram new [name]` | Create new diagram |
| `/diagram export png` | Export current as PNG |
| `/diagram export pptx` | Export current as PowerPoint |
| `/tasks` | Switch back to task mode |

---

## Hotkey Consistency

Both modes share these hotkeys:

| Key | Tasks Mode | Diagrams Mode |
|-----|------------|---------------|
| Arrow keys | Navigate tiles | Navigate nodes |
| 1-9 | Focus tile | Focus node |
| Enter | Drill into parent task | Drill into node |
| Escape | Zoom out / clear | Zoom out |
| Space | Toggle select | Toggle select |
| / | Command bar | Command bar |
| ? | Help | Help |
| Tab | Cycle panels | Cycle panels |

Diagram-specific:
| Key | Action |
|-----|--------|
| c | Connect nodes |
| e | Edit node |
| n | New node |
| x | Delete |

---

## Acceptance Criteria

- [ ] `/diagram` command switches to diagram mode
- [ ] Diagram picker shows available .json files
- [ ] Selecting diagram loads and renders it
- [ ] Arrow keys navigate between nodes
- [ ] Enter drills into nodes with children
- [ ] Escape zooms out
- [ ] Breadcrumb shows layer path
- [ ] `/tasks` switches back to task mode
- [ ] Nodes with task_id show linked task in context panel
- [ ] Status bar shows diagram name and layer

---

## Build Instructions

Tell Claude Code:

```
Read docs/plans/interactive-architecture-diagrams/phase-5-command-centre-integration.md

Create the diagram mode for Command Centre:
1. Create brain/command_centre/modes/diagrams.py
2. Create brain/command_centre/widgets/diagram_grid.py
3. Add /diagram handler to router.py
4. Update app.py with mode switching

Ensure hotkeys are consistent with existing task mode. Test by running Command Centre, typing /diagram, and navigating a sample diagram.
```
