# Phase 2: Editing and Data Management

## Goal

Edit nodes and connections directly in the browser. Save and load diagram data as JSON files.

## Prerequisites

- Phase 1 complete and validated
- Keyboard navigation feels natural
- Drill-down/zoom-out works smoothly

## Deliverables

- [ ] Click node to edit label inline
- [ ] Double-click to edit description
- [ ] Drag nodes to reposition (in freeform mode)
- [ ] Connection creation mode (c key)
- [ ] Delete nodes/connections (x key)
- [ ] Add new node (n key)
- [ ] Save button → downloads JSON file
- [ ] Load button → imports JSON file
- [ ] Undo/redo (Ctrl+Z / Ctrl+Shift+Z)

---

## Technical Specification

### Inline Editing

```javascript
function enableInlineEdit(nodeEl) {
    const labelEl = nodeEl.querySelector('.node-label');
    const originalText = labelEl.textContent;
    
    labelEl.contentEditable = true;
    labelEl.focus();
    
    // Select all text
    const range = document.createRange();
    range.selectNodeContents(labelEl);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    
    labelEl.addEventListener('blur', () => {
        labelEl.contentEditable = false;
        const newText = labelEl.textContent.trim();
        if (newText !== originalText) {
            updateNodeLabel(nodeEl.dataset.id, newText);
            pushUndoState();
        }
    });
    
    labelEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            labelEl.blur();
        }
        if (e.key === 'Escape') {
            labelEl.textContent = originalText;
            labelEl.blur();
        }
    });
}
```

### Drag to Reposition (Freeform Mode)

```javascript
let isDragging = false;
let dragNode = null;
let dragOffset = {x: 0, y: 0};

function enableDrag(nodeEl) {
    nodeEl.addEventListener('mousedown', (e) => {
        if (DIAGRAM_DATA.meta.gridMode === 'freeform') {
            isDragging = true;
            dragNode = nodeEl;
            const rect = nodeEl.getBoundingClientRect();
            dragOffset = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
            nodeEl.classList.add('dragging');
        }
    });
}

document.addEventListener('mousemove', (e) => {
    if (isDragging && dragNode) {
        const canvas = document.getElementById('canvas');
        const canvasRect = canvas.getBoundingClientRect();
        
        const x = e.clientX - canvasRect.left - dragOffset.x;
        const y = e.clientY - canvasRect.top - dragOffset.y;
        
        dragNode.style.position = 'absolute';
        dragNode.style.left = `${x}px`;
        dragNode.style.top = `${y}px`;
        
        // Re-render connections as node moves
        renderConnections();
    }
});

document.addEventListener('mouseup', () => {
    if (isDragging && dragNode) {
        isDragging = false;
        dragNode.classList.remove('dragging');
        
        // Update node position in data
        const nodeId = dragNode.dataset.id;
        const rect = dragNode.getBoundingClientRect();
        const canvasRect = document.getElementById('canvas').getBoundingClientRect();
        
        updateNodePosition(nodeId, {
            x: rect.left - canvasRect.left,
            y: rect.top - canvasRect.top
        });
        
        pushUndoState();
        dragNode = null;
    }
});
```

### Connection Creation Mode

```javascript
let connectionMode = false;
let connectionSource = null;

function startConnectionMode() {
    connectionMode = true;
    connectionSource = null;
    document.body.classList.add('connection-mode');
    showStatus('Click source node, then target node. Escape to cancel.');
}

function handleNodeClickInConnectionMode(nodeId) {
    if (!connectionSource) {
        connectionSource = nodeId;
        document.querySelector(`[data-id="${nodeId}"]`).classList.add('connection-source');
        showStatus(`Source: ${getNodeLabel(nodeId)}. Now click target node.`);
    } else {
        // Create connection
        const newConnection = {
            id: `conn-${Date.now()}`,
            from: connectionSource,
            to: nodeId,
            type: 'data-flow',
            label: '',
            style: 'arrow-one-way',
            colour: '#8b949e'
        };
        
        DIAGRAM_DATA.connections.push(newConnection);
        renderConnections();
        pushUndoState();
        
        // Exit connection mode
        exitConnectionMode();
        showStatus(`Connection created: ${getNodeLabel(connectionSource)} → ${getNodeLabel(nodeId)}`);
    }
}

function exitConnectionMode() {
    connectionMode = false;
    connectionSource = null;
    document.body.classList.remove('connection-mode');
    document.querySelectorAll('.connection-source').forEach(el => el.classList.remove('connection-source'));
}

// Keyboard handler
document.addEventListener('keydown', (e) => {
    if (e.key === 'c' && !connectionMode) {
        startConnectionMode();
    }
    if (e.key === 'Escape' && connectionMode) {
        exitConnectionMode();
        showStatus('Connection cancelled.');
    }
});
```

### Delete Node/Connection

```javascript
function deleteSelected() {
    const selectedNodes = document.querySelectorAll('.node.selected');
    const selectedConnections = document.querySelectorAll('.connection.selected');
    
    if (selectedNodes.length === 0 && selectedConnections.length === 0) {
        // Delete focused node
        const focused = document.querySelector('.node:focus');
        if (focused) {
            deleteNode(focused.dataset.id);
        }
        return;
    }
    
    selectedNodes.forEach(nodeEl => {
        deleteNode(nodeEl.dataset.id);
    });
    
    selectedConnections.forEach(connEl => {
        deleteConnection(connEl.dataset.id);
    });
    
    pushUndoState();
    renderLayer(currentLayer);
}

function deleteNode(nodeId) {
    // Remove node
    DIAGRAM_DATA.nodes = DIAGRAM_DATA.nodes.filter(n => n.id !== nodeId);
    
    // Remove from layers
    Object.values(DIAGRAM_DATA.layers).forEach(layer => {
        layer.visible = layer.visible.filter(id => id !== nodeId);
    });
    
    // Remove connections to/from this node
    DIAGRAM_DATA.connections = DIAGRAM_DATA.connections.filter(c => 
        c.from !== nodeId && c.to !== nodeId
    );
    
    // Remove from parent's children
    DIAGRAM_DATA.nodes.forEach(n => {
        if (n.children) {
            n.children = n.children.filter(id => id !== nodeId);
        }
    });
}
```

### Add New Node

```javascript
function addNewNode() {
    const layer = DIAGRAM_DATA.layers[currentLayer];
    const visibleCount = layer.visible.length;
    
    // Calculate grid position
    const gridCols = DIAGRAM_DATA.meta.gridCols || 6;
    const col = visibleCount % gridCols;
    const row = Math.floor(visibleCount / gridCols);
    
    const newNode = {
        id: `node-${Date.now()}`,
        label: 'New Node',
        type: 'capability',
        icon: 'box',
        colour: '#21262d',
        gridPos: {col, row, colSpan: 1, rowSpan: 1},
        parent: currentLayer === 'overview' ? null : currentLayer,
        children: [],
        meta: {}
    };
    
    DIAGRAM_DATA.nodes.push(newNode);
    layer.visible.push(newNode.id);
    
    pushUndoState();
    renderLayer(currentLayer);
    
    // Focus and start editing the new node
    setTimeout(() => {
        const nodeEl = document.querySelector(`[data-id="${newNode.id}"]`);
        nodeEl.focus();
        enableInlineEdit(nodeEl);
    }, 100);
}
```

### Undo/Redo

```javascript
const undoStack = [];
const redoStack = [];
const MAX_UNDO = 50;

function pushUndoState() {
    undoStack.push(JSON.stringify(DIAGRAM_DATA));
    if (undoStack.length > MAX_UNDO) {
        undoStack.shift();
    }
    redoStack.length = 0; // Clear redo on new action
    updateUndoRedoButtons();
}

function undo() {
    if (undoStack.length > 0) {
        redoStack.push(JSON.stringify(DIAGRAM_DATA));
        DIAGRAM_DATA = JSON.parse(undoStack.pop());
        renderLayer(currentLayer);
        showStatus('Undone');
    }
}

function redo() {
    if (redoStack.length > 0) {
        undoStack.push(JSON.stringify(DIAGRAM_DATA));
        DIAGRAM_DATA = JSON.parse(redoStack.pop());
        renderLayer(currentLayer);
        showStatus('Redone');
    }
}

document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
        if (e.key === 'z' && !e.shiftKey) {
            e.preventDefault();
            undo();
        }
        if ((e.key === 'z' && e.shiftKey) || e.key === 'y') {
            e.preventDefault();
            redo();
        }
    }
});
```

### Save/Load JSON

```javascript
function saveDiagram() {
    const json = JSON.stringify(DIAGRAM_DATA, null, 2);
    const blob = new Blob([json], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `${DIAGRAM_DATA.meta.title.toLowerCase().replace(/\s+/g, '-')}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
    showStatus('Diagram saved');
}

function loadDiagram() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = (e) => {
        const file = e.target.files[0];
        const reader = new FileReader();
        
        reader.onload = (event) => {
            try {
                const data = JSON.parse(event.target.result);
                
                // Validate structure
                if (!data.meta || !data.nodes || !data.connections || !data.layers) {
                    throw new Error('Invalid diagram format');
                }
                
                DIAGRAM_DATA = data;
                currentLayer = 'overview';
                layerStack = ['overview'];
                undoStack.length = 0;
                redoStack.length = 0;
                
                renderLayer(currentLayer);
                updateBreadcrumb();
                showStatus(`Loaded: ${data.meta.title}`);
            } catch (err) {
                showStatus(`Error loading file: ${err.message}`, 'error');
            }
        };
        
        reader.readAsText(file);
    };
    
    input.click();
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveDiagram();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'o') {
        e.preventDefault();
        loadDiagram();
    }
});
```

---

## Updated Keyboard Map

| Key | Action |
|-----|--------|
| e | Edit focused node label |
| n | Add new node |
| c | Start connection mode |
| x | Delete selected/focused |
| Ctrl+S | Save diagram |
| Ctrl+O | Load diagram |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |

---

## UI Updates

### Toolbar

```html
<header id="toolbar">
    <nav id="breadcrumb"></nav>
    <div id="toolbar-buttons">
        <button id="btn-add" title="Add node (n)">
            <i data-lucide="plus"></i>
        </button>
        <button id="btn-connect" title="Connect (c)">
            <i data-lucide="link"></i>
        </button>
        <button id="btn-delete" title="Delete (x)">
            <i data-lucide="trash-2"></i>
        </button>
        <span class="separator"></span>
        <button id="btn-undo" title="Undo (Ctrl+Z)" disabled>
            <i data-lucide="undo"></i>
        </button>
        <button id="btn-redo" title="Redo (Ctrl+Shift+Z)" disabled>
            <i data-lucide="redo"></i>
        </button>
        <span class="separator"></span>
        <button id="btn-save" title="Save (Ctrl+S)">
            <i data-lucide="save"></i>
        </button>
        <button id="btn-load" title="Load (Ctrl+O)">
            <i data-lucide="folder-open"></i>
        </button>
    </div>
</header>
```

---

## Acceptance Criteria

- [ ] Press e to edit node label inline
- [ ] Enter confirms edit, Escape cancels
- [ ] Press n to add new node at next grid position
- [ ] Press c to enter connection mode
- [ ] Click two nodes to create connection
- [ ] Press x to delete focused node
- [ ] Deleting node removes its connections
- [ ] Ctrl+Z undoes last action
- [ ] Ctrl+Shift+Z redoes
- [ ] Ctrl+S downloads JSON file
- [ ] Ctrl+O loads JSON file
- [ ] Loaded diagram renders correctly
- [ ] All changes persist through save/load cycle

---

## Build Instructions

Tell Claude Code:

```
Read docs/plans/interactive-architecture-diagrams/phase-2-editing.md

Update docs/tools/diagram-viewer.html to add editing capabilities.

Keep all existing navigation working. Add the toolbar buttons and keyboard shortcuts for editing.

Test by: adding a node, editing its label, connecting it to another node, saving, reloading, and verifying the connection persists.
```
