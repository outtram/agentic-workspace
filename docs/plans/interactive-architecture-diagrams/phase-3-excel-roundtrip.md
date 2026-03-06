# Phase 3: Excel Round-Trip

## Goal

Export diagrams to Excel for bulk editing in a spreadsheet, then re-import. This enables:
- Bulk updates to node labels, colours, metadata
- Easy data entry for large diagrams
- Collaboration with people who prefer spreadsheets
- Version control via Excel file history

## Prerequisites

- Phase 2 complete
- Save/load JSON working
- Undo/redo working

## Deliverables

- [ ] Export to .xlsx with two sheets (Nodes, Connections)
- [ ] Import .xlsx and rebuild diagram
- [ ] Validation on import (missing IDs, broken connections)
- [ ] Merge mode (update existing vs replace all)
- [ ] Export template (empty sheets with headers)

---

## Technical Specification

### Library: SheetJS (xlsx)

```html
<script src="https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js"></script>
```

### Excel Schema

**Sheet 1: Nodes**

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| id | string | Yes | Unique identifier |
| label | string | Yes | Display name |
| description | string | No | Longer description |
| type | string | Yes | capability, sub-capability, channel, etc. |
| icon | string | No | Lucide icon name |
| colour | string | No | Hex colour (#FF6B35) |
| col | number | Yes | Grid column (0-based) |
| row | number | Yes | Grid row (0-based) |
| colSpan | number | No | Column span (default 1) |
| rowSpan | number | No | Row span (default 1) |
| parent | string | No | Parent node ID |
| layer | string | No | Which layer this appears in |
| meta_* | string | No | Custom metadata fields |

**Sheet 2: Connections**

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| id | string | Yes | Unique identifier |
| from | string | Yes | Source node ID |
| to | string | Yes | Target node ID |
| type | string | No | data-flow, dependency, etc. |
| label | string | No | Connection label |
| style | string | No | arrow-one-way, arrow-two-way, line, dashed |
| colour | string | No | Hex colour |

### Export to Excel

```javascript
function exportToExcel() {
    // Prepare nodes sheet
    const nodesData = DIAGRAM_DATA.nodes.map(node => {
        const row = {
            id: node.id,
            label: node.label,
            description: node.description || '',
            type: node.type,
            icon: node.icon || '',
            colour: node.colour || '',
            col: node.gridPos?.col ?? 0,
            row: node.gridPos?.row ?? 0,
            colSpan: node.gridPos?.colSpan ?? 1,
            rowSpan: node.gridPos?.rowSpan ?? 1,
            parent: node.parent || '',
            layer: findNodeLayer(node.id)
        };
        
        // Add meta fields
        if (node.meta) {
            Object.entries(node.meta).forEach(([key, value]) => {
                row[`meta_${key}`] = value;
            });
        }
        
        return row;
    });
    
    // Prepare connections sheet
    const connectionsData = DIAGRAM_DATA.connections.map(conn => ({
        id: conn.id,
        from: conn.from,
        to: conn.to,
        type: conn.type || '',
        label: conn.label || '',
        style: conn.style || 'arrow-one-way',
        colour: conn.colour || ''
    }));
    
    // Create workbook
    const wb = XLSX.utils.book_new();
    
    const nodesSheet = XLSX.utils.json_to_sheet(nodesData);
    XLSX.utils.book_append_sheet(wb, nodesSheet, 'Nodes');
    
    const connectionsSheet = XLSX.utils.json_to_sheet(connectionsData);
    XLSX.utils.book_append_sheet(wb, connectionsSheet, 'Connections');
    
    // Add metadata sheet
    const metaData = [
        {key: 'title', value: DIAGRAM_DATA.meta.title},
        {key: 'gridMode', value: DIAGRAM_DATA.meta.gridMode},
        {key: 'gridCols', value: DIAGRAM_DATA.meta.gridCols},
        {key: 'gridRows', value: DIAGRAM_DATA.meta.gridRows}
    ];
    const metaSheet = XLSX.utils.json_to_sheet(metaData);
    XLSX.utils.book_append_sheet(wb, metaSheet, 'Meta');
    
    // Download
    const filename = `${DIAGRAM_DATA.meta.title.toLowerCase().replace(/\s+/g, '-')}.xlsx`;
    XLSX.writeFile(wb, filename);
    
    showStatus(`Exported to ${filename}`);
}

function findNodeLayer(nodeId) {
    for (const [layerId, layer] of Object.entries(DIAGRAM_DATA.layers)) {
        if (layer.visible.includes(nodeId)) {
            return layerId;
        }
    }
    return 'overview';
}
```

### Import from Excel

```javascript
function importFromExcel(file, mode = 'replace') {
    const reader = new FileReader();
    
    reader.onload = (e) => {
        try {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, {type: 'array'});
            
            // Read sheets
            const nodesSheet = workbook.Sheets['Nodes'];
            const connectionsSheet = workbook.Sheets['Connections'];
            const metaSheet = workbook.Sheets['Meta'];
            
            if (!nodesSheet || !connectionsSheet) {
                throw new Error('Missing required sheets (Nodes, Connections)');
            }
            
            const nodesData = XLSX.utils.sheet_to_json(nodesSheet);
            const connectionsData = XLSX.utils.sheet_to_json(connectionsSheet);
            const metaData = metaSheet ? XLSX.utils.sheet_to_json(metaSheet) : [];
            
            // Validate
            const errors = validateImport(nodesData, connectionsData);
            if (errors.length > 0) {
                showValidationErrors(errors);
                return;
            }
            
            // Convert to diagram format
            const newDiagram = convertExcelToDiagram(nodesData, connectionsData, metaData);
            
            if (mode === 'replace') {
                DIAGRAM_DATA = newDiagram;
            } else if (mode === 'merge') {
                mergeDiagram(newDiagram);
            }
            
            // Rebuild layers from node data
            rebuildLayers();
            
            pushUndoState();
            currentLayer = 'overview';
            layerStack = ['overview'];
            renderLayer(currentLayer);
            updateBreadcrumb();
            
            showStatus(`Imported ${nodesData.length} nodes, ${connectionsData.length} connections`);
            
        } catch (err) {
            showStatus(`Import error: ${err.message}`, 'error');
            console.error(err);
        }
    };
    
    reader.readAsArrayBuffer(file);
}

function validateImport(nodes, connections) {
    const errors = [];
    const nodeIds = new Set(nodes.map(n => n.id));
    
    // Check required fields
    nodes.forEach((node, i) => {
        if (!node.id) errors.push(`Row ${i+2}: Missing node ID`);
        if (!node.label) errors.push(`Row ${i+2}: Missing label for ${node.id}`);
        if (!node.type) errors.push(`Row ${i+2}: Missing type for ${node.id}`);
    });
    
    // Check for duplicate IDs
    const seen = new Set();
    nodes.forEach(node => {
        if (seen.has(node.id)) {
            errors.push(`Duplicate node ID: ${node.id}`);
        }
        seen.add(node.id);
    });
    
    // Check connection references
    connections.forEach((conn, i) => {
        if (!conn.from) errors.push(`Connection row ${i+2}: Missing 'from'`);
        if (!conn.to) errors.push(`Connection row ${i+2}: Missing 'to'`);
        if (conn.from && !nodeIds.has(conn.from)) {
            errors.push(`Connection row ${i+2}: Unknown source node '${conn.from}'`);
        }
        if (conn.to && !nodeIds.has(conn.to)) {
            errors.push(`Connection row ${i+2}: Unknown target node '${conn.to}'`);
        }
    });
    
    // Check parent references
    nodes.forEach(node => {
        if (node.parent && !nodeIds.has(node.parent)) {
            errors.push(`Node ${node.id}: Unknown parent '${node.parent}'`);
        }
    });
    
    return errors;
}

function convertExcelToDiagram(nodesData, connectionsData, metaData) {
    // Convert meta
    const meta = {
        title: 'Imported Diagram',
        gridMode: 'strict',
        gridCols: 6,
        gridRows: 4
    };
    metaData.forEach(row => {
        if (row.key && row.value !== undefined) {
            meta[row.key] = row.value;
        }
    });
    
    // Convert nodes
    const nodes = nodesData.map(row => {
        const node = {
            id: row.id,
            label: row.label,
            description: row.description || '',
            type: row.type || 'capability',
            icon: row.icon || 'box',
            colour: row.colour || '#21262d',
            gridPos: {
                col: parseInt(row.col) || 0,
                row: parseInt(row.row) || 0,
                colSpan: parseInt(row.colSpan) || 1,
                rowSpan: parseInt(row.rowSpan) || 1
            },
            parent: row.parent || null,
            children: [],
            meta: {}
        };
        
        // Extract meta fields
        Object.keys(row).forEach(key => {
            if (key.startsWith('meta_')) {
                const metaKey = key.replace('meta_', '');
                node.meta[metaKey] = row[key];
            }
        });
        
        return node;
    });
    
    // Build children arrays from parent references
    nodes.forEach(node => {
        if (node.parent) {
            const parent = nodes.find(n => n.id === node.parent);
            if (parent) {
                parent.children.push(node.id);
            }
        }
    });
    
    // Convert connections
    const connections = connectionsData.map(row => ({
        id: row.id || `conn-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        from: row.from,
        to: row.to,
        type: row.type || 'data-flow',
        label: row.label || '',
        style: row.style || 'arrow-one-way',
        colour: row.colour || '#8b949e'
    }));
    
    return {meta, nodes, connections, layers: {}};
}

function rebuildLayers() {
    // Build layers from node parent relationships
    const layers = {
        overview: {
            title: DIAGRAM_DATA.meta.title || 'Overview',
            visible: []
        }
    };
    
    DIAGRAM_DATA.nodes.forEach(node => {
        if (!node.parent) {
            // Top-level node goes in overview
            layers.overview.visible.push(node.id);
        } else {
            // Child node goes in parent's layer
            if (!layers[node.parent]) {
                const parentNode = DIAGRAM_DATA.nodes.find(n => n.id === node.parent);
                layers[node.parent] = {
                    title: parentNode?.label || node.parent,
                    visible: []
                };
            }
            layers[node.parent].visible.push(node.id);
        }
    });
    
    DIAGRAM_DATA.layers = layers;
}
```

### Validation Error Display

```javascript
function showValidationErrors(errors) {
    const overlay = document.getElementById('help-overlay');
    overlay.classList.remove('hidden');
    overlay.innerHTML = `
        <div class="validation-errors">
            <h2>Import Validation Errors</h2>
            <p>Fix these issues in the Excel file and try again:</p>
            <ul>
                ${errors.map(e => `<li>${e}</li>`).join('')}
            </ul>
            <button onclick="document.getElementById('help-overlay').classList.add('hidden')">Close</button>
        </div>
    `;
}
```

### Export Template

```javascript
function exportTemplate() {
    const wb = XLSX.utils.book_new();
    
    // Nodes template with example row
    const nodesTemplate = [
        {
            id: 'example-1',
            label: 'Example Node',
            description: 'Description here',
            type: 'capability',
            icon: 'box',
            colour: '#FF6B35',
            col: 0,
            row: 0,
            colSpan: 1,
            rowSpan: 1,
            parent: '',
            layer: 'overview',
            meta_owner: 'Name',
            meta_status: 'live'
        }
    ];
    
    // Connections template with example
    const connectionsTemplate = [
        {
            id: 'conn-example',
            from: 'example-1',
            to: 'example-2',
            type: 'data-flow',
            label: 'connection label',
            style: 'arrow-one-way',
            colour: '#8b949e'
        }
    ];
    
    // Meta template
    const metaTemplate = [
        {key: 'title', value: 'My Diagram'},
        {key: 'gridMode', value: 'strict'},
        {key: 'gridCols', value: 6},
        {key: 'gridRows', value: 4}
    ];
    
    const nodesSheet = XLSX.utils.json_to_sheet(nodesTemplate);
    XLSX.utils.book_append_sheet(wb, nodesSheet, 'Nodes');
    
    const connectionsSheet = XLSX.utils.json_to_sheet(connectionsTemplate);
    XLSX.utils.book_append_sheet(wb, connectionsSheet, 'Connections');
    
    const metaSheet = XLSX.utils.json_to_sheet(metaTemplate);
    XLSX.utils.book_append_sheet(wb, metaSheet, 'Meta');
    
    XLSX.writeFile(wb, 'diagram-template.xlsx');
    showStatus('Template downloaded');
}
```

---

## Updated Toolbar

```html
<div id="toolbar-buttons">
    <!-- ... existing buttons ... -->
    <span class="separator"></span>
    <button id="btn-export-excel" title="Export to Excel">
        <i data-lucide="file-spreadsheet"></i>
        Excel
    </button>
    <button id="btn-import-excel" title="Import from Excel">
        <i data-lucide="upload"></i>
        Import
    </button>
    <button id="btn-template" title="Download template">
        <i data-lucide="file-plus"></i>
        Template
    </button>
</div>
```

---

## Acceptance Criteria

- [ ] Export creates .xlsx with Nodes, Connections, Meta sheets
- [ ] All node fields are exported correctly
- [ ] All connection fields are exported correctly
- [ ] Import reads .xlsx and rebuilds diagram
- [ ] Validation catches missing required fields
- [ ] Validation catches broken node references
- [ ] Validation catches duplicate IDs
- [ ] Errors display clearly with row numbers
- [ ] Template download works
- [ ] Round-trip: export → edit in Excel → import preserves data

---

## Build Instructions

Tell Claude Code:

```
Read docs/plans/interactive-architecture-diagrams/phase-3-excel-roundtrip.md

Update docs/tools/diagram-viewer.html to add Excel import/export.

Add SheetJS from CDN. Add toolbar buttons for Export Excel, Import, and Template.

Test by: exporting current diagram, opening in Excel, changing a node label, saving, importing, and verifying the change appears.
```
