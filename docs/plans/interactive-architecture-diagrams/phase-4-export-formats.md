# Phase 4: Export Formats

## Goal

Export diagrams as PNG images and PowerPoint presentations for sharing with stakeholders who don't use the interactive viewer.

## Prerequisites

- Phase 2 complete (editing works)
- Phase 3 complete (Excel round-trip works)

## Deliverables

- [ ] PNG export via html2canvas
- [ ] PPTX export via PptxGenJS
- [ ] Export current layer only
- [ ] Export all layers as multi-slide deck
- [ ] Export options dialog (size, quality, theme)

---

## Technical Specification

### Libraries

```html
<!-- PNG export -->
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>

<!-- PowerPoint export -->
<script src="https://cdn.jsdelivr.net/npm/pptxgenjs@3.12.0/dist/pptxgen.bundle.js"></script>
```

### PNG Export

```javascript
async function exportToPNG(options = {}) {
    const {
        scale = 2,           // 2x for retina quality
        backgroundColor = '#0d1117',
        filename = null
    } = options;
    
    // Hide UI elements we don't want in export
    const toolbar = document.getElementById('toolbar');
    const statusBar = document.getElementById('status-bar');
    const helpOverlay = document.getElementById('help-overlay');
    
    toolbar.style.display = 'none';
    statusBar.style.display = 'none';
    helpOverlay.classList.add('hidden');
    
    // Remove focus styling
    document.querySelectorAll('.node').forEach(n => n.blur());
    
    try {
        const canvas = await html2canvas(document.getElementById('canvas'), {
            scale: scale,
            backgroundColor: backgroundColor,
            useCORS: true,
            logging: false
        });
        
        // Convert to blob and download
        canvas.toBlob((blob) => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename || `${DIAGRAM_DATA.meta.title}-${currentLayer}.png`;
            a.click();
            URL.revokeObjectURL(url);
            showStatus('PNG exported');
        }, 'image/png');
        
    } finally {
        // Restore UI
        toolbar.style.display = '';
        statusBar.style.display = '';
    }
}
```

### PowerPoint Export

```javascript
async function exportToPPTX(options = {}) {
    const {
        allLayers = false,
        slideWidth = 13.33,   // 16:9 aspect ratio
        slideHeight = 7.5,
        theme = 'dark'
    } = options;
    
    const pptx = new PptxGenJS();
    
    // Set presentation properties
    pptx.title = DIAGRAM_DATA.meta.title;
    pptx.author = 'Diagram Viewer';
    pptx.layout = 'LAYOUT_16x9';
    
    // Define theme colours
    const colours = theme === 'dark' ? {
        background: '0D1117',
        text: 'E6EDF3',
        textMuted: '8B949E',
        accent1: 'FF6B35',
        accent2: '00D4AA',
        nodeBg: '21262D',
        nodeBorder: '30363D'
    } : {
        background: 'FFFFFF',
        text: '1F2328',
        textMuted: '656D76',
        accent1: 'FF6B35',
        accent2: '00D4AA',
        nodeBg: 'F6F8FA',
        nodeBorder: 'D0D7DE'
    };
    
    if (allLayers) {
        // Export all layers as separate slides
        for (const [layerId, layer] of Object.entries(DIAGRAM_DATA.layers)) {
            await addSlideForLayer(pptx, layerId, layer, colours);
        }
    } else {
        // Export current layer only
        const layer = DIAGRAM_DATA.layers[currentLayer];
        await addSlideForLayer(pptx, currentLayer, layer, colours);
    }
    
    // Download
    const filename = `${DIAGRAM_DATA.meta.title.toLowerCase().replace(/\s+/g, '-')}.pptx`;
    await pptx.writeFile({fileName: filename});
    showStatus(`PowerPoint exported: ${filename}`);
}

async function addSlideForLayer(pptx, layerId, layer, colours) {
    const slide = pptx.addSlide();
    
    // Set background
    slide.background = {color: colours.background};
    
    // Add title
    slide.addText(layer.title || layerId, {
        x: 0.5,
        y: 0.3,
        w: '90%',
        h: 0.5,
        fontSize: 24,
        bold: true,
        color: colours.accent1
    });
    
    // Calculate grid dimensions
    const gridCols = DIAGRAM_DATA.meta.gridCols || 6;
    const gridRows = DIAGRAM_DATA.meta.gridRows || 4;
    
    const gridLeft = 0.5;
    const gridTop = 1.0;
    const gridWidth = 12.33;
    const gridHeight = 5.5;
    
    const cellWidth = gridWidth / gridCols;
    const cellHeight = gridHeight / gridRows;
    const padding = 0.1;
    
    // Get visible nodes for this layer
    const visibleNodes = layer.visible
        .map(id => DIAGRAM_DATA.nodes.find(n => n.id === id))
        .filter(Boolean);
    
    // Add nodes as shapes
    visibleNodes.forEach(node => {
        const x = gridLeft + (node.gridPos.col * cellWidth) + padding;
        const y = gridTop + (node.gridPos.row * cellHeight) + padding;
        const w = (node.gridPos.colSpan || 1) * cellWidth - (padding * 2);
        const h = (node.gridPos.rowSpan || 1) * cellHeight - (padding * 2);
        
        // Determine shape type
        let shapeType = 'rect';
        let shapeOpts = {rectRadius: 0.1};
        
        if (node.type === 'decision') {
            shapeType = 'diamond';
            shapeOpts = {};
        } else if (node.type === 'channel') {
            shapeType = 'ellipse';
            shapeOpts = {};
        }
        
        // Add shape
        slide.addShape(pptx.ShapeType[shapeType] || pptx.ShapeType.rect, {
            x: x,
            y: y,
            w: w,
            h: h,
            fill: {color: node.colour?.replace('#', '') || colours.nodeBg},
            line: {color: colours.nodeBorder, width: 1},
            ...shapeOpts
        });
        
        // Add label
        slide.addText(node.label, {
            x: x,
            y: y + (h / 2) - 0.2,
            w: w,
            h: 0.4,
            fontSize: 11,
            bold: true,
            color: colours.text,
            align: 'center',
            valign: 'middle'
        });
        
        // Add status badge if present
        if (node.meta?.status) {
            const statusColour = node.meta.status === 'live' ? colours.accent2 :
                                 node.meta.status === 'in-progress' ? colours.accent1 :
                                 colours.textMuted;
            slide.addText(node.meta.status, {
                x: x + w - 0.8,
                y: y + 0.1,
                w: 0.7,
                h: 0.25,
                fontSize: 8,
                color: statusColour,
                align: 'right'
            });
        }
    });
    
    // Add connections as lines
    const visibleNodeIds = new Set(layer.visible);
    const visibleConnections = DIAGRAM_DATA.connections.filter(c =>
        visibleNodeIds.has(c.from) && visibleNodeIds.has(c.to)
    );
    
    visibleConnections.forEach(conn => {
        const fromNode = DIAGRAM_DATA.nodes.find(n => n.id === conn.from);
        const toNode = DIAGRAM_DATA.nodes.find(n => n.id === conn.to);
        
        if (!fromNode || !toNode) return;
        
        // Calculate centre points
        const fromX = gridLeft + (fromNode.gridPos.col + 0.5) * cellWidth;
        const fromY = gridTop + (fromNode.gridPos.row + 0.5) * cellHeight;
        const toX = gridLeft + (toNode.gridPos.col + 0.5) * cellWidth;
        const toY = gridTop + (toNode.gridPos.row + 0.5) * cellHeight;
        
        // Determine line style
        const lineOpts = {
            color: conn.colour?.replace('#', '') || colours.textMuted,
            width: 1.5
        };
        
        if (conn.style === 'dashed') {
            lineOpts.dashType = 'dash';
        }
        
        // Add line
        slide.addShape(pptx.ShapeType.line, {
            x: fromX,
            y: fromY,
            w: toX - fromX,
            h: toY - fromY,
            line: lineOpts
        });
        
        // Add arrowhead (as a small triangle at end)
        if (conn.style?.includes('arrow')) {
            const angle = Math.atan2(toY - fromY, toX - fromX);
            const arrowSize = 0.15;
            
            // This is simplified - real implementation would calculate proper arrow position
            slide.addShape(pptx.ShapeType.triangle, {
                x: toX - arrowSize,
                y: toY - arrowSize / 2,
                w: arrowSize,
                h: arrowSize,
                rotate: (angle * 180 / Math.PI) + 90,
                fill: {color: conn.colour?.replace('#', '') || colours.textMuted}
            });
        }
        
        // Add label if present
        if (conn.label) {
            const midX = (fromX + toX) / 2;
            const midY = (fromY + toY) / 2;
            
            slide.addText(conn.label, {
                x: midX - 0.5,
                y: midY - 0.3,
                w: 1,
                h: 0.25,
                fontSize: 8,
                color: colours.textMuted,
                align: 'center'
            });
        }
    });
    
    // Add breadcrumb/layer path at bottom
    slide.addText(`Layer: ${layerId}`, {
        x: 0.5,
        y: 6.8,
        w: '50%',
        h: 0.3,
        fontSize: 10,
        color: colours.textMuted
    });
}
```

### Export Options Dialog

```javascript
function showExportDialog() {
    const overlay = document.getElementById('help-overlay');
    overlay.classList.remove('hidden');
    overlay.innerHTML = `
        <div class="export-dialog">
            <h2>Export Diagram</h2>
            
            <div class="export-section">
                <h3>PNG Image</h3>
                <div class="export-options">
                    <label>
                        Scale:
                        <select id="png-scale">
                            <option value="1">1x (standard)</option>
                            <option value="2" selected>2x (retina)</option>
                            <option value="3">3x (high-res)</option>
                        </select>
                    </label>
                </div>
                <button onclick="exportPNGWithOptions()">
                    <i data-lucide="image"></i> Export PNG
                </button>
            </div>
            
            <div class="export-section">
                <h3>PowerPoint</h3>
                <div class="export-options">
                    <label>
                        <input type="checkbox" id="pptx-all-layers">
                        Export all layers (multi-slide)
                    </label>
                    <label>
                        Theme:
                        <select id="pptx-theme">
                            <option value="dark" selected>Dark</option>
                            <option value="light">Light</option>
                        </select>
                    </label>
                </div>
                <button onclick="exportPPTXWithOptions()">
                    <i data-lucide="presentation"></i> Export PPTX
                </button>
            </div>
            
            <button class="close-btn" onclick="closeExportDialog()">Cancel</button>
        </div>
    `;
    lucide.createIcons();
}

function exportPNGWithOptions() {
    const scale = parseInt(document.getElementById('png-scale').value);
    closeExportDialog();
    exportToPNG({scale});
}

function exportPPTXWithOptions() {
    const allLayers = document.getElementById('pptx-all-layers').checked;
    const theme = document.getElementById('pptx-theme').value;
    closeExportDialog();
    exportToPPTX({allLayers, theme});
}

function closeExportDialog() {
    document.getElementById('help-overlay').classList.add('hidden');
}
```

### Export Dialog Styles

```css
.export-dialog {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 24px;
    max-width: 400px;
    margin: 0 auto;
}

.export-dialog h2 {
    margin-top: 0;
    color: var(--accent-orange);
}

.export-dialog h3 {
    color: var(--text-primary);
    font-size: 14px;
    margin-bottom: 8px;
}

.export-section {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 16px;
    margin-bottom: 16px;
}

.export-options {
    margin-bottom: 12px;
}

.export-options label {
    display: block;
    margin-bottom: 8px;
    color: var(--text-secondary);
    font-size: 13px;
}

.export-options select {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    color: var(--text-primary);
    padding: 4px 8px;
    margin-left: 8px;
}

.export-section button {
    width: 100%;
    padding: 10px;
    background: var(--accent-orange);
    color: var(--bg-primary);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}

.export-section button:hover {
    opacity: 0.9;
}

.close-btn {
    width: 100%;
    padding: 10px;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    cursor: pointer;
}
```

---

## Updated Toolbar

```html
<div id="toolbar-buttons">
    <!-- ... existing buttons ... -->
    <span class="separator"></span>
    <button id="btn-export" title="Export (Ctrl+E)">
        <i data-lucide="download"></i>
        Export
    </button>
</div>
```

---

## Keyboard Shortcut

```javascript
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
        e.preventDefault();
        showExportDialog();
    }
});
```

---

## Acceptance Criteria

- [ ] Ctrl+E opens export dialog
- [ ] PNG export captures current layer
- [ ] PNG scale options work (1x, 2x, 3x)
- [ ] PNG excludes toolbar and status bar
- [ ] PPTX export creates valid PowerPoint file
- [ ] PPTX nodes render as shapes with labels
- [ ] PPTX connections render as lines
- [ ] PPTX "all layers" creates multiple slides
- [ ] PPTX dark/light theme options work
- [ ] Exported PPTX opens in PowerPoint/Keynote

---

## Build Instructions

Tell Claude Code:

```
Read docs/plans/interactive-architecture-diagrams/phase-4-export-formats.md

Update docs/tools/diagram-viewer.html to add PNG and PowerPoint export.

Add html2canvas and PptxGenJS from CDN. Add Export button to toolbar that opens options dialog.

Test by: exporting current diagram as PNG (verify image quality), then as PPTX (verify it opens in PowerPoint with correct shapes and connections).
```
