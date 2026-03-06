# Phase 1: Static Prototype

## Goal

Build a single HTML file that renders a hardcoded diagram with grid, drill-down, and connections. **No editing, no export yet.** Just prove the interaction model works.

## Deliverables

- [ ] Grid rendering with CSS Grid
- [ ] Node types: box, icon-box, circle, diamond
- [ ] Connection rendering with SVG paths
- [ ] Keyboard navigation (arrows, Enter to drill, Escape to zoom out)
- [ ] Breadcrumb navigation
- [ ] Embedded JSON data
- [ ] Help overlay (? key)

## Output File

```
docs/tools/diagram-viewer.html
```

Single self-contained HTML file. No external dependencies except CDN links for icons.

---

## Technical Specification

### HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Diagram Viewer</title>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>/* All CSS inline */</style>
</head>
<body>
    <div id="app">
        <header id="toolbar">
            <nav id="breadcrumb"></nav>
            <div id="diagram-title"></div>
        </header>
        
        <main id="canvas">
            <div id="grid"></div>
            <svg id="connections"></svg>
        </main>
        
        <footer id="status-bar">
            <span id="layer-info"></span>
            <span id="selection-info"></span>
            <span id="help-hint">Press ? for help</span>
        </footer>
        
        <div id="help-overlay" class="hidden"></div>
    </div>
    
    <script>
        const DIAGRAM_DATA = { /* embedded JSON */ };
        // All JS inline
    </script>
</body>
</html>
```

### CSS Grid Layout

```css
#canvas {
    position: relative;
    width: 100%;
    height: calc(100vh - 120px);
    overflow: hidden;
}

#grid {
    display: grid;
    grid-template-columns: repeat(var(--grid-cols, 6), 1fr);
    grid-template-rows: repeat(var(--grid-rows, 4), 1fr);
    gap: 16px;
    padding: 24px;
    height: 100%;
}

#connections {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
}
```

### Node Rendering

Each node is a `<div>` positioned in the grid:

```html
<div class="node" 
     data-id="cap-1" 
     data-type="capability"
     style="grid-column: 1 / span 1; grid-row: 1 / span 1;"
     tabindex="0">
    <div class="node-icon">
        <i data-lucide="user-plus"></i>
    </div>
    <div class="node-label">Customer Onboarding</div>
    <div class="node-badge" data-status="live">Live</div>
</div>
```

### Node Styles

```css
.node {
    background: var(--node-bg, #21262d);
    border: 2px solid var(--node-border, #30363d);
    border-radius: 8px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.15s ease;
}

.node:focus {
    outline: none;
    border-color: var(--accent-orange, #FF6B35);
    box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.3);
}

.node.selected {
    border-color: var(--accent-teal, #00D4AA);
    background: rgba(0, 212, 170, 0.1);
}

.node.has-children::after {
    content: '▼';
    position: absolute;
    bottom: 4px;
    right: 8px;
    font-size: 10px;
    color: var(--text-muted);
}

.node[data-type="decision"] {
    border-radius: 0;
    transform: rotate(45deg);
}

.node[data-type="decision"] > * {
    transform: rotate(-45deg);
}

.node[data-type="channel"] {
    border-radius: 50px;
}

.node[data-type="external"] {
    border-style: dashed;
}
```

### Connection Rendering (SVG)

Connections are drawn as SVG paths between node centres:

```javascript
function renderConnections(visibleNodes, connections) {
    const svg = document.getElementById('connections');
    svg.innerHTML = '';
    
    connections.forEach(conn => {
        const fromNode = document.querySelector(`[data-id="${conn.from}"]`);
        const toNode = document.querySelector(`[data-id="${conn.to}"]`);
        
        if (!fromNode || !toNode) return;
        
        const fromRect = fromNode.getBoundingClientRect();
        const toRect = toNode.getBoundingClientRect();
        const canvasRect = svg.getBoundingClientRect();
        
        const x1 = fromRect.left + fromRect.width/2 - canvasRect.left;
        const y1 = fromRect.top + fromRect.height/2 - canvasRect.top;
        const x2 = toRect.left + toRect.width/2 - canvasRect.left;
        const y2 = toRect.top + toRect.height/2 - canvasRect.top;
        
        const path = createOrthogonalPath(x1, y1, x2, y2);
        
        const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        pathEl.setAttribute('d', path);
        pathEl.setAttribute('stroke', conn.colour || '#8b949e');
        pathEl.setAttribute('stroke-width', '2');
        pathEl.setAttribute('fill', 'none');
        
        if (conn.style === 'dashed') {
            pathEl.setAttribute('stroke-dasharray', '5,5');
        }
        
        // Add arrowhead
        if (conn.style.includes('arrow')) {
            pathEl.setAttribute('marker-end', 'url(#arrowhead)');
        }
        if (conn.style === 'arrow-two-way') {
            pathEl.setAttribute('marker-start', 'url(#arrowhead-reverse)');
        }
        
        svg.appendChild(pathEl);
        
        // Add label if present
        if (conn.label) {
            const midX = (x1 + x2) / 2;
            const midY = (y1 + y2) / 2;
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', midX);
            text.setAttribute('y', midY - 8);
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('fill', '#8b949e');
            text.setAttribute('font-size', '12');
            text.textContent = conn.label;
            svg.appendChild(text);
        }
    });
}

function createOrthogonalPath(x1, y1, x2, y2) {
    // Simple orthogonal routing: go right, then down/up
    const midX = (x1 + x2) / 2;
    return `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`;
}
```

### Keyboard Navigation

```javascript
let focusedNodeIndex = 0;
let currentLayer = 'overview';
const layerStack = ['overview'];

document.addEventListener('keydown', (e) => {
    const visibleNodes = getVisibleNodes();
    
    switch(e.key) {
        case 'ArrowRight':
            focusedNodeIndex = Math.min(focusedNodeIndex + 1, visibleNodes.length - 1);
            focusNode(visibleNodes[focusedNodeIndex]);
            break;
        case 'ArrowLeft':
            focusedNodeIndex = Math.max(focusedNodeIndex - 1, 0);
            focusNode(visibleNodes[focusedNodeIndex]);
            break;
        case 'ArrowDown':
            focusedNodeIndex = Math.min(focusedNodeIndex + gridCols, visibleNodes.length - 1);
            focusNode(visibleNodes[focusedNodeIndex]);
            break;
        case 'ArrowUp':
            focusedNodeIndex = Math.max(focusedNodeIndex - gridCols, 0);
            focusNode(visibleNodes[focusedNodeIndex]);
            break;
        case 'Enter':
            drillInto(visibleNodes[focusedNodeIndex]);
            break;
        case 'Escape':
        case 'Backspace':
            zoomOut();
            e.preventDefault();
            break;
        case ' ':
            toggleSelect(visibleNodes[focusedNodeIndex]);
            e.preventDefault();
            break;
        case '?':
            toggleHelp();
            break;
        default:
            // Number keys 1-9 for direct node access
            if (e.key >= '1' && e.key <= '9') {
                const index = parseInt(e.key) - 1;
                if (index < visibleNodes.length) {
                    focusedNodeIndex = index;
                    focusNode(visibleNodes[index]);
                }
            }
    }
});

function drillInto(nodeId) {
    const node = DIAGRAM_DATA.nodes.find(n => n.id === nodeId);
    if (node && node.children && node.children.length > 0) {
        layerStack.push(nodeId);
        currentLayer = nodeId;
        focusedNodeIndex = 0;
        renderLayer(currentLayer);
        updateBreadcrumb();
    }
}

function zoomOut() {
    if (layerStack.length > 1) {
        layerStack.pop();
        currentLayer = layerStack[layerStack.length - 1];
        focusedNodeIndex = 0;
        renderLayer(currentLayer);
        updateBreadcrumb();
    }
}

function updateBreadcrumb() {
    const breadcrumb = document.getElementById('breadcrumb');
    breadcrumb.innerHTML = layerStack.map((layerId, i) => {
        const layer = DIAGRAM_DATA.layers[layerId];
        const title = layer?.title || layerId;
        const isLast = i === layerStack.length - 1;
        return `<span class="crumb ${isLast ? 'current' : ''}" data-layer="${layerId}">${title}</span>`;
    }).join(' <span class="separator">›</span> ');
}
```

### Layer Rendering

```javascript
function renderLayer(layerId) {
    const grid = document.getElementById('grid');
    grid.innerHTML = '';
    
    const layer = DIAGRAM_DATA.layers[layerId];
    const visibleNodeIds = layer?.visible || [];
    
    visibleNodeIds.forEach(nodeId => {
        const node = DIAGRAM_DATA.nodes.find(n => n.id === nodeId);
        if (node) {
            grid.appendChild(createNodeElement(node));
        }
    });
    
    // Re-initialize Lucide icons
    lucide.createIcons();
    
    // Render connections for visible nodes
    const visibleConnections = DIAGRAM_DATA.connections.filter(c => 
        visibleNodeIds.includes(c.from) && visibleNodeIds.includes(c.to)
    );
    renderConnections(visibleNodeIds, visibleConnections);
    
    // Focus first node
    const firstNode = grid.querySelector('.node');
    if (firstNode) firstNode.focus();
}
```

### Help Overlay

```javascript
function toggleHelp() {
    const overlay = document.getElementById('help-overlay');
    overlay.classList.toggle('hidden');
    
    if (!overlay.classList.contains('hidden')) {
        overlay.innerHTML = `
            <div class="help-content">
                <h2>Keyboard Shortcuts</h2>
                <table>
                    <tr><td><kbd>←</kbd> <kbd>→</kbd> <kbd>↑</kbd> <kbd>↓</kbd></td><td>Navigate between nodes</td></tr>
                    <tr><td><kbd>1</kbd>-<kbd>9</kbd></td><td>Jump to node by position</td></tr>
                    <tr><td><kbd>Enter</kbd></td><td>Drill into node (show children)</td></tr>
                    <tr><td><kbd>Escape</kbd> / <kbd>Backspace</kbd></td><td>Zoom out one layer</td></tr>
                    <tr><td><kbd>Space</kbd></td><td>Select/deselect node</td></tr>
                    <tr><td><kbd>?</kbd></td><td>Toggle this help</td></tr>
                </table>
                <p class="help-footer">Press any key to close</p>
            </div>
        `;
    }
}
```

---

## Sample Data (Embedded)

```javascript
const DIAGRAM_DATA = {
    meta: {
        title: "Program Capability Map",
        gridMode: "strict",
        gridCols: 4,
        gridRows: 3
    },
    nodes: [
        {
            id: "cap-onboarding",
            label: "Customer Onboarding",
            type: "capability",
            icon: "user-plus",
            colour: "#FF6B35",
            gridPos: {col: 0, row: 0, colSpan: 1, rowSpan: 1},
            parent: null,
            children: ["cap-kyc", "cap-account", "cap-welcome"],
            meta: {owner: "Kate", status: "live"}
        },
        {
            id: "cap-servicing",
            label: "Account Servicing",
            type: "capability",
            icon: "settings",
            colour: "#00D4AA",
            gridPos: {col: 1, row: 0, colSpan: 1, rowSpan: 1},
            parent: null,
            children: [],
            meta: {owner: "Mike", status: "live"}
        },
        {
            id: "cap-payments",
            label: "Payments",
            type: "capability",
            icon: "credit-card",
            colour: "#FF6B35",
            gridPos: {col: 2, row: 0, colSpan: 1, rowSpan: 1},
            parent: null,
            children: ["cap-bpay", "cap-transfer", "cap-international"],
            meta: {owner: "Sarah", status: "in-progress"}
        },
        {
            id: "cap-support",
            label: "Customer Support",
            type: "capability",
            icon: "headphones",
            colour: "#00D4AA",
            gridPos: {col: 3, row: 0, colSpan: 1, rowSpan: 1},
            parent: null,
            children: [],
            meta: {owner: "Tom", status: "planned"}
        },
        {
            id: "cap-mobile",
            label: "Mobile App",
            type: "channel",
            icon: "smartphone",
            colour: "#8b949e",
            gridPos: {col: 0, row: 1, colSpan: 1, rowSpan: 1},
            parent: null,
            children: [],
            meta: {status: "live"}
        },
        {
            id: "cap-web",
            label: "Web Portal",
            type: "channel",
            icon: "globe",
            colour: "#8b949e",
            gridPos: {col: 1, row: 1, colSpan: 1, rowSpan: 1},
            parent: null,
            children: [],
            meta: {status: "live"}
        },
        // Children of Onboarding
        {
            id: "cap-kyc",
            label: "KYC Verification",
            type: "sub-capability",
            icon: "shield-check",
            colour: "#FF6B35",
            gridPos: {col: 0, row: 0, colSpan: 1, rowSpan: 1},
            parent: "cap-onboarding",
            children: [],
            meta: {status: "live"}
        },
        {
            id: "cap-account",
            label: "Account Creation",
            type: "sub-capability",
            icon: "user",
            colour: "#FF6B35",
            gridPos: {col: 1, row: 0, colSpan: 1, rowSpan: 1},
            parent: "cap-onboarding",
            children: [],
            meta: {status: "live"}
        },
        {
            id: "cap-welcome",
            label: "Welcome Journey",
            type: "sub-capability",
            icon: "mail",
            colour: "#00D4AA",
            gridPos: {col: 2, row: 0, colSpan: 1, rowSpan: 1},
            parent: "cap-onboarding",
            children: [],
            meta: {status: "in-progress"}
        },
        // Children of Payments
        {
            id: "cap-bpay",
            label: "BPAY",
            type: "sub-capability",
            icon: "receipt",
            colour: "#FF6B35",
            gridPos: {col: 0, row: 0, colSpan: 1, rowSpan: 1},
            parent: "cap-payments",
            children: [],
            meta: {status: "live"}
        },
        {
            id: "cap-transfer",
            label: "Transfers",
            type: "sub-capability",
            icon: "arrow-right-left",
            colour: "#FF6B35",
            gridPos: {col: 1, row: 0, colSpan: 1, rowSpan: 1},
            parent: "cap-payments",
            children: [],
            meta: {status: "live"}
        },
        {
            id: "cap-international",
            label: "International",
            type: "sub-capability",
            icon: "globe",
            colour: "#00D4AA",
            gridPos: {col: 2, row: 0, colSpan: 1, rowSpan: 1},
            parent: "cap-payments",
            children: [],
            meta: {status: "planned"}
        }
    ],
    connections: [
        {
            id: "conn-1",
            from: "cap-onboarding",
            to: "cap-servicing",
            type: "data-flow",
            label: "customer created",
            style: "arrow-one-way",
            colour: "#8b949e"
        },
        {
            id: "conn-2",
            from: "cap-servicing",
            to: "cap-payments",
            type: "dependency",
            label: "",
            style: "arrow-one-way",
            colour: "#8b949e"
        },
        {
            id: "conn-3",
            from: "cap-mobile",
            to: "cap-onboarding",
            type: "channel",
            label: "",
            style: "line",
            colour: "#30363d"
        },
        {
            id: "conn-4",
            from: "cap-mobile",
            to: "cap-payments",
            type: "channel",
            label: "",
            style: "line",
            colour: "#30363d"
        },
        {
            id: "conn-5",
            from: "cap-web",
            to: "cap-onboarding",
            type: "channel",
            label: "",
            style: "line",
            colour: "#30363d"
        },
        {
            id: "conn-6",
            from: "cap-web",
            to: "cap-servicing",
            type: "channel",
            label: "",
            style: "line",
            colour: "#30363d"
        },
        // Connections within Onboarding layer
        {
            id: "conn-7",
            from: "cap-kyc",
            to: "cap-account",
            type: "sequence",
            label: "verified",
            style: "arrow-one-way",
            colour: "#FF6B35"
        },
        {
            id: "conn-8",
            from: "cap-account",
            to: "cap-welcome",
            type: "sequence",
            label: "created",
            style: "arrow-one-way",
            colour: "#FF6B35"
        }
    ],
    layers: {
        overview: {
            title: "Program Overview",
            visible: ["cap-onboarding", "cap-servicing", "cap-payments", "cap-support", "cap-mobile", "cap-web"]
        },
        "cap-onboarding": {
            title: "Customer Onboarding",
            visible: ["cap-kyc", "cap-account", "cap-welcome"]
        },
        "cap-payments": {
            title: "Payments",
            visible: ["cap-bpay", "cap-transfer", "cap-international"]
        }
    }
};
```

---

## Acceptance Criteria

- [ ] Page loads with 6 nodes in a 4x3 grid
- [ ] Arrow keys move focus (orange border) between nodes
- [ ] Number keys 1-6 jump directly to nodes
- [ ] Enter on "Customer Onboarding" shows 3 child nodes
- [ ] Escape returns to overview
- [ ] Breadcrumb shows "Overview > Customer Onboarding"
- [ ] Connections render as lines between nodes
- [ ] Arrow connections have arrowheads
- [ ] Connection labels appear at midpoint
- [ ] ? key shows help overlay
- [ ] Styling matches Command Centre (dark theme, orange/teal accents)

---

## Build Instructions

Tell Claude Code:

```
Read docs/plans/interactive-architecture-diagrams/phase-1-static-prototype.md

Build the diagram viewer as a single HTML file at docs/tools/diagram-viewer.html

Use the embedded sample data. Match the Command Centre styling (dark theme, orange #FF6B35, teal #00D4AA).

Focus on keyboard navigation first - it must feel as smooth as the Command Centre tile grid.
```
