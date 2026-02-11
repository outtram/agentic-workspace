# PowerPoint Diagram Layout Guide

## Slide Layouts

### Title Slide
- Architecture title
- System name
- Date/version
- Author/team
- Context (Current State/Future State/Target Architecture)

### Overview/Context Slide
- High-level system context
- Key stakeholders
- Major external systems
- Business objectives

### Detailed Architecture Slides
- One layer per slide (UI, Services, Data)
- Component groupings by domain
- Clear data flow arrows
- Technology stack labels

### Component Detail Slides
- Individual service/component deep-dives
- API specifications
- Data models
- Dependencies

## Layout Principles

### CRITICAL: Consistent Alignment Across Slides

**All slides must use identical margins:**
- Left margin: 0.5 inches
- Right margin: 0.5 inches
- Content width: 9 inches (10 - 0.5 - 0.5)
- **NEVER vary margins between slides**

**Component alignment rules:**
1. All components in a row must start at same X position (left-aligned)
2. All components in a row must be same width or proportionally spaced
3. Components spanning full width should go from leftMargin to rightMargin
4. Multi-component rows should divide contentWidth equally with small gaps (0.05-0.1")

**Example for 4 equal components:**
```
componentWidth = (contentWidth - (3 * gap)) / 4
Component 1: X = leftMargin
Component 2: X = leftMargin + (componentWidth + gap)
Component 3: X = leftMargin + 2*(componentWidth + gap)
Component 4: X = leftMargin + 3*(componentWidth + gap)
```

**Visual alignment checklist:**
- [ ] All slides use same leftMargin and contentWidth
- [ ] Components in each layer aligned to same grid
- [ ] Full-width components span entire contentWidth
- [ ] Multi-component rows evenly divided
- [ ] Text boxes aligned with component edges
- [ ] Footer text uses same margins as content

### Grid System
- Use PowerPoint's built-in grid (View > Gridlines)
- Align components to grid intersections
- Consistent spacing between elements
- Group related components visually

### Hierarchy
- Larger shapes for major components
- Smaller shapes for supporting services
- Z-order layering (background to foreground)
- Color intensity to show importance

### Flow Direction
- Left-to-right for process flow
- Top-to-bottom for system layers
- Center-out for hub-and-spoke
- Consistent arrow directions

## Shape Guidelines

### Rectangles
- **Rounded rectangles**: Applications, services (2-3" wide, 1-1.5" tall)
- **Sharp rectangles**: Databases, storage (1.5-2" wide, 1-1.5" tall)
- **Thin rectangles**: API endpoints (3-4" wide, 0.5" tall)

### Connectors
- **Solid arrows**: Direct API calls
- **Dashed arrows**: Async messaging
- **Thick lines (3pt)**: High-volume data
- **Standard lines (1.5pt)**: Normal flow
- **Curved connectors**: Avoid overlaps

### Positioning
- **Standard spacing**: 0.5" between related components
- **Group spacing**: 1" between different domains
- **Margin**: 0.5" from slide edges
- **Alignment**: Center major components, align edges for groups

## Color Application

### Background Colors
- **Light blue (#E3F2FD)**: Services, APIs
- **Light green (#E8F5E9)**: Databases
- **Light orange (#FFF3E0)**: UI components
- **Light purple (#F3E5F5)**: External services
- **Light gray (#F5F5F5)**: Infrastructure

### Border Colors
- Use darker shades of background colors
- 2-3pt borders for visibility
- Match border to component type

### Text Colors
- **Black (#000000)**: Component names
- **Dark gray (#424242)**: Technology labels
- **Medium gray (#757575)**: Descriptions

## Typography

### Fonts
- **Titles**: Segoe UI, Calibri, or Arial
- **Body**: Same as titles for consistency
- **Code/Tech**: Consolas or Courier New

### Sizes
- **Slide titles**: 32pt bold
- **Section headers**: 24pt bold
- **Component names**: 14pt bold
- **Technology labels**: 10pt italic
- **Annotations**: 9pt regular

## Layout Templates

### Layout Templates

### Layer-Based Layout (Horizontal Tiers)

**CRITICAL: Calculate vertical space before building**

Example for 4-layer architecture:
```
Title:          Y = 0.2",  H = 0.5"   → ends at 0.7"
Layer 1 Label:  Y = 0.85", H = 0.25"  → ends at 1.1"
Layer 1 Comps:  Y = 1.15", H = 0.5"   → ends at 1.65"
Arrow:          Y = 1.75", H = 0.15"  → ends at 1.9"
Layer 2 Label:  Y = 1.95", H = 0.25"  → ends at 2.2"
Layer 2 Comps:  Y = 2.25", H = 0.45"  → ends at 2.7"
Arrow:          Y = 2.8",  H = 0.15"  → ends at 2.95"
Layer 3 Label:  Y = 3.0",  H = 0.25"  → ends at 3.25"
Layer 3 Comps:  Y = 3.3",  H = 0.5"   → ends at 3.8"
Arrow:          Y = 3.9",  H = 0.15"  → ends at 4.05"
Layer 4 Label:  Y = 4.1",  H = 0.25"  → ends at 4.35"
Layer 4 Comps:  Y = 4.4",  H = 0.5"   → ends at 4.9"
Footer:         Y = 5.35", H = 0.15"  → ends at 5.5"
TOTAL: 5.5" ✓ (within 5.625" limit)
```

**Visual representation:**
```
+--------------------------------------------------+
|              UI Layer (Orange)                   |
+--------------------------------------------------+
                       ↓
+--------------------------------------------------+
|              API Layer (Blue)                    |
+--------------------------------------------------+
                       ↓
+--------------------------------------------------+
|            Services Layer (Blue)                 |
+--------------------------------------------------+
                       ↓
+--------------------------------------------------+
|             Data Layer (Green)                   |
+--------------------------------------------------+
```

### Domain-Based Layout (Vertical Columns)
```
+------------+  +------------+  +------------+
|  Domain A  |  |  Domain B  |  |  Domain C  |
|            |  |            |  |            |
| [Services] |  | [Services] |  | [Services] |
| [Database] |  | [Database] |  | [Database] |
+------------+  +------------+  +------------+
```

### Hub-and-Spoke Layout (Centered)
```
        [Service A]
             |
    [Service B] -- [API Gateway] -- [Service C]
             |
        [Service D]
```

## Best Practices

### Critical: Prevent Vertical Overflow
**ALWAYS calculate total height before creating slides**
- 16:9 slides are 5.625" tall
- Leave 0.1-0.2" margin at bottom
- For 4-layer diagrams: max 1.3" per layer (including gaps)
- For 5-layer diagrams: max 1.0" per layer (including gaps)
- **Test formula: (Title + All Layers + Footer) < 5.5"**

### Avoid
- Overlapping shapes
- Crossing arrows (use bridges or curves)
- Too many colors (stick to 3-4 main colors)
- Tiny text (< 9pt)
- Dense slides (> 15 components per slide)
- **Vertical overflow (content beyond 5.625")**
- **Not calculating total height before building**

### Do
- Group related components
- Use consistent spacing
- Label all connections
- Add legends when needed
- Include technology stack callouts
- Version your diagrams
- Add "as of" dates
- **Calculate vertical layout before creating shapes**
- **Compress spacing for multi-layer diagrams**
- **Test: Last element Y-position + height < 5.5"**
