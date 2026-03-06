# Interactive Architecture Diagram System

> A grid-based, keyboard-driven diagram tool for mapping capabilities, journeys, and system architecture with drill-down layers and complex connections.

## Quick Links

- [Master Plan](./00-master-plan.md) - Overview, architecture, data model
- [Phase 1: Static Prototype](./phase-1-static-prototype.md) - Grid, nodes, connections, navigation
- [Phase 2: Editing](./phase-2-editing.md) - Inline editing, drag-drop, save/load
- [Phase 3: Excel Round-Trip](./phase-3-excel-roundtrip.md) - Spreadsheet import/export
- [Phase 4: Export Formats](./phase-4-export-formats.md) - PNG, PowerPoint export
- [Phase 5: Command Centre](./phase-5-command-centre-integration.md) - TUI integration

## Current Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 | **TODO** | Start here - validate the concept |
| Phase 2 | Blocked | Depends on Phase 1 validation |
| Phase 3 | Blocked | Depends on Phase 2 |
| Phase 4 | Blocked | Depends on Phase 2 |
| Phase 5 | Blocked | Depends on Phase 1-4 |

## Build Command

Once Phase 1 is approved, tell Claude Code:

```
Read docs/plans/interactive-architecture-diagrams/phase-1-static-prototype.md and build it
```

## Output Location

- **Standalone HTML:** `docs/tools/diagram-viewer.html`
- **Diagram data files:** `.claude/diagrams/*.json`
- **Command Centre integration:** `brain/command_centre/diagram_mode.py`
