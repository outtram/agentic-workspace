# Interactive Architecture Diagram System - Master Plan

## Overview

Build a prototype interactive diagram system with:
- Grid-based navigation (like Command Centre tile grid)
- Drill-down layers (Enter to go deeper, Escape to zoom out)
- Complex connections (arrows, lines, labels, multiple styles)
- Multiple editing modes (inline, YAML/JSON, Excel)
- Multiple export formats (HTML, PNG, PowerPoint)

## Why This Matters

Troy's workflow involves mapping 15+ capabilities across channels and journeys. Current tools (Miro, draw.io, PowerPoint) lack:
- Keyboard-first navigation
- Hierarchical drill-down
- Easy bulk editing via spreadsheet
- Consistent styling with Command Centre

## Concept Validation

This is a **good idea**. The Command Centre architecture viewer proves the grid + drill-down pattern works. Extending it to arbitrary diagrams with connections is a natural evolution.

**Risks to manage:**
- Connection routing complexity → mitigated by using proven layout libraries
- Excel round-trip fidelity → mitigated by simple two-sheet model
- Scope creep → mitigated by prototype-first approach

---

## Architecture

### Data Model (JSON)

```json
{
  "meta": {
    "title": "Program Capability Map",
    "gridMode": "strict",
    "gridCols": 6,
    "gridRows": 4,
    "defaultZoom": "overview",
    "theme": {
      "background": "#0d1117",
      "nodeDefault": "#21262d",
      "accent1": "#FF6B35",
      "accent2": "#00D4AA",
      "text": "#e6edf3",
      "textMuted": "#8b949e"
    }
  },
  "nodes": [
    {
      "id": "cap-1",
      "label": "Customer Onboarding",
      "description": "End-to-end onboarding journey",
      "type": "capability",
      "icon": "user-plus",
      "colour": "#FF6B35",
      "gridPos": {"col": 0, "row": 0, "colSpan": 1, "rowSpan": 1},
      "parent": null,
      "children": ["cap-1a", "cap-1b", "cap-1c"],
      "meta": {
        "owner": "Kate",
        "status": "live",
        "channel": "web"
      }
    },
    {
      "id": "cap-1a",
      "label": "Identity Verification",
      "type": "sub-capability",
      "icon": "shield-check",
      "colour": "#00D4AA",
      "gridPos": {"col": 0, "row": 0, "colSpan": 1, "rowSpan": 1},
      "parent": "cap-1",
      "children": [],
      "meta": {"status": "in-progress"}
    }
  ],
  "connections": [
    {
      "id": "conn-1",
      "from": "cap-1",
      "to": "cap-2",
      "type": "data-flow",
      "label": "customer record",
      "style": "arrow-one-way",
      "colour": "#8b949e"
    },
    {
      "id": "conn-2",
      "from": "cap-2",
      "to": "cap-3",
      "type": "dependency",
      "label": "",
      "style": "arrow-two-way",
      "colour": "#FF6B35"
    }
  ],
  "layers": {
    "overview": {
      "title": "Program Overview",
      "visible": ["cap-1", "cap-2", "cap-3", "cap-4", "cap-5"]
    },
    "cap-1": {
      "title": "Customer Onboarding",
      "visible": ["cap-1a", "cap-1b", "cap-1c"]
    }
  }
}
```

### Node Types

| Type | Shape | Use Case |
|------|-------|----------|
| `capability` | Rounded rectangle | Top-level capabilities |
| `sub-capability` | Rounded rectangle (smaller) | Nested capabilities |
| `system` | Rectangle with icon | Technical systems |
| `channel` | Pill/oval | Communication channels |
| `journey-step` | Circle | Steps in a journey |
| `decision` | Diamond | Decision points |
| `external` | Dashed rectangle | External systems/parties |

### Connection Styles

| Style | Visual | Use Case |
|-------|--------|----------|
| `arrow-one-way` | →  | Data flow, dependency |
| `arrow-two-way` | ↔  | Bidirectional flow |
| `line` | —  | Association, grouping |
| `dashed` | - - - | Optional, future |
| `thick` | ═══ | Primary flow |

### Excel Schema (Two Sheets)

**Sheet 1: Nodes**

| id | label | description | type | icon | colour | col | row | colSpan | rowSpan | parent | meta_owner | meta_status | meta_channel |
|----|-------|-------------|------|------|--------|-----|-----|---------|---------|--------|------------|-------------|--------------|
| cap-1 | Customer Onboarding | End-to-end journey | capability | user-plus | #FF6B35 | 0 | 0 | 1 | 1 | | Kate | live | web |

**Sheet 2: Connections**

| id | from | to | type | label | style | colour |
|----|------|----|----- |-------|-------|--------|
| conn-1 | cap-1 | cap-2 | data-flow | customer record | arrow-one-way | #8b949e |

---

## Technology Stack

| Component | Library | Why |
|-----------|---------|-----|
| Rendering | Vanilla JS + CSS Grid | Simple, no build step |
| Connections | SVG paths | Native, crisp at any zoom |
| Connection routing | Manual orthogonal | Control over aesthetics |
| Icons | Lucide | Same as Command Centre |
| PNG export | html2canvas | Proven, simple |
| PPTX export | PptxGenJS | Native PowerPoint shapes |
| Excel I/O | SheetJS (xlsx) | Industry standard |

---

## Interaction Model

### Keyboard Navigation

| Key | Action |
|-----|--------|
| Arrow keys | Move focus between nodes |
| 1-9 | Jump to node by grid position |
| Enter | Drill into focused node (show children) |
| Escape | Zoom out one layer |
| Backspace | Zoom out one layer (alternative) |
| Tab | Cycle focus: nodes → toolbar |
| Space | Select/deselect node |
| Shift+Space | Add to multi-selection |
| c | Start connection mode |
| e | Edit focused node inline |
| x | Delete focused node/connection |
| Ctrl+S | Save diagram |
| Ctrl+E | Export menu |
| ? | Show help overlay |

### Mouse Interaction

| Action | Result |
|--------|--------|
| Click node | Focus node |
| Double-click node | Drill into node |
| Click + drag node | Move node (freeform mode) |
| Click connection | Select connection |
| Right-click | Context menu |

### Layers and Drill-Down

1. Each node can have a `children` array
2. Enter on a node with children → view transitions to show only those children
3. Breadcrumb trail shows: `Overview > Customer Onboarding > KYC Process`
4. Escape goes back up the breadcrumb
5. Connections between visible nodes are shown; others are hidden

---

## File Structure

```
docs/plans/interactive-architecture-diagrams/
├── README.md                              # This index
├── 00-master-plan.md                      # Architecture, data model
├── phase-1-static-prototype.md            # Build instructions
├── phase-2-editing.md                     # Editing features
├── phase-3-excel-roundtrip.md             # Excel import/export
├── phase-4-export-formats.md              # PNG, PPTX export
├── phase-5-command-centre-integration.md  # TUI integration
└── sample-data/
    ├── capability-map.json                # Sample diagram
    └── system-architecture.json           # Sample diagram

docs/tools/
└── diagram-viewer.html                    # Standalone prototype

.claude/diagrams/
├── program-capabilities.json              # Real diagrams
└── system-architecture.json

brain/command_centre/
└── diagram_mode.py                        # Phase 5 integration
```

---

## Phase Summary

| Phase | Goal | Deliverables | Effort |
|-------|------|--------------|--------|
| 1 | Validate concept | Static HTML with grid, drill-down, connections | 4-6 hours |
| 2 | Enable editing | Inline edit, drag, save/load JSON | 4-6 hours |
| 3 | Excel workflow | Import/export .xlsx | 3-4 hours |
| 4 | Sharing | PNG + PPTX export | 3-4 hours |
| 5 | Integration | Command Centre diagram mode | 4-6 hours |

**Total estimated effort:** 18-26 hours across all phases

---

## Open Design Questions

1. **Grid size:** Default 6x4? 8x6? Configurable per diagram?
2. **Connection routing:** Orthogonal only, or allow curved paths?
3. **Colour palette:** Command Centre colours, or custom per diagram?
4. **Multi-select:** What operations work on multiple nodes?
5. **Undo/redo:** Essential for Phase 2, or defer to Phase 3?

---

## Success Criteria

**Phase 1 is successful if:**
- [ ] Grid renders correctly with 6+ nodes
- [ ] Keyboard navigation feels natural (like Command Centre)
- [ ] Drill-down/zoom-out works smoothly
- [ ] Connections render without overlapping nodes
- [ ] Troy uses it for a real capability map within 1 week
