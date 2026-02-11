---
name: pptx-arch-diagrams
description: Create professional enterprise system architecture and technology diagrams in PowerPoint. Use when users request architectural diagrams, system diagrams, technology stack visualizations, microservices architecture diagrams, multi-tier architecture, data flow diagrams, deployment diagrams, or any technical system visualization in PowerPoint format.
---

# PowerPoint Architectural Diagrams

## Overview

Create professional, enterprise-grade system architecture and technology diagrams in PowerPoint format. This skill provides patterns, layouts, and visual conventions for common architectural diagram types including microservices, multi-tier, event-driven, and multi-channel digital ecosystems.

## Before Starting

**CRITICAL**: Read reference files completely before creating diagrams:
- `references/arch-patterns.md` - Common architectural patterns and component categories
- `references/layout-guide.md` - PowerPoint-specific layout and design principles
- `references/pptx-skill.md` - Core PowerPoint creation workflow

## Quick Start Workflow

### 1. Understand Requirements
Ask clarifying questions:
- What type of architecture? (microservices, 3-tier, event-driven, etc.)
- Current state, future state, or both?
- Level of detail needed? (overview, detailed components, or deep-dive)
- Specific technologies to highlight?
- Any existing diagrams to reference?

### 2. Create Diagram Structure

Use HTML-to-PPTX workflow for best results:

```python
# Install html2pptx if needed
pip install html2pptx --break-system-packages

# Create HTML with diagram structure
# Then convert to PPTX
html2pptx diagram.html output.pptx
```

### 3. Standard Slide Structure

**Title Slide**
- Architecture name
- System/project name
- Current/Future state designation
- Date and version

**Context Slide**
- Business objectives
- Key stakeholders
- System boundaries
- External dependencies

**Architecture Slides** (1-3 slides depending on complexity)
- Layer-based views (UI → Services → Data)
- Component groupings by domain
- Data flow visualization
- Technology stack callouts

**Detail Slides** (as needed)
- Individual component deep-dives
- Integration patterns
- Deployment views

## Common Diagram Types

### Microservices Architecture
Components to include:
- API Gateway
- Individual microservices (grouped by domain)
- Service mesh/communication layer
- Databases (one per service or shared)
- Message brokers/event streams
- Load balancers
- Monitoring & logging

Layout: Grid layout with services grouped by domain, arrows showing sync/async communication

### Multi-Channel Digital Ecosystem
Components to include:
- Channel layer: Website, iOS app, Android app, portals
- API Gateway
- Core services layer (grouped by function)
- Data platform layer
- Integration layer for external systems

Layout: Horizontal layers (top-down: channels → APIs → services → data)

### Three-Tier Architecture
Components to include:
- Presentation tier: Web/mobile interfaces
- Business logic tier: Application servers, APIs
- Data tier: Databases, caching, storage

Layout: Three horizontal bands with clear separation

### Event-Driven Architecture
Components to include:
- Event producers
- Event streaming platform (Kafka, etc.)
- Event processors/consumers
- Event store
- Command/Query handlers

Layout: Left-to-right flow showing event lifecycle

## Visual Design Standards

### Color Scheme
- **Blue** (#0078D4): API Gateway, infrastructure
- **Teal** (#008080): Core services, microservices
- **Orange** (#FF8C00): User interfaces, channels, endpoints
- **Green** (#107C10): Databases, storage, data platforms
- **Purple** (#5C2D91): CMS platforms, external services, third-party integrations
- **Red** (#E81123): Security services, monitoring, alerts
- **Gray** (#767676): Infrastructure, networking, supporting services

### Shape Standards
- **Rounded rectangles**: Applications, services, APIs
- **Cylinders**: Databases, data stores
- **Clouds**: Cloud platforms, external services
- **Hexagons**: API endpoints, gateways
- **Circles**: Users, external actors
- **Diamonds**: Decision points, routing logic

### Connector Standards
- **Solid arrows**: Synchronous calls (REST, gRPC)
- **Dashed arrows**: Asynchronous messaging (events, queues)
- **Thick lines**: High-volume data flow
- **Thin lines**: Control flow, configuration
- **Bi-directional**: Two-way communication

### Text Standards
- **Component names**: Bold, 12-14pt
- **Technology labels**: Italic, 10pt, gray
- **Arrows**: 8-10pt annotations
- **Slide titles**: 28-32pt, bold

## Layout Principles

### Grid & Alignment
- Enable PowerPoint grid (View → Gridlines)
- Align all shapes to grid intersections
- Consistent spacing: 0.25-0.5 inches between components
- Group related components with visual proximity

### Hierarchy & Flow
- Larger shapes for critical/major components
- Top-to-bottom for architectural layers
- Left-to-right for process/data flow
- Z-order: background elements behind foreground

### Grouping
- Group components by business domain
- Use subtle background rectangles for domains
- Color-code groups consistently
- Label groups clearly

## Creating with HTML2PPTX

### CRITICAL: Slide Dimensions and Layout Constraints

**PowerPoint 16:9 Format:**
- Width: 10 inches
- Height: 5.625 inches
- **NEVER exceed these dimensions** - content will be cut off

**Vertical Spacing Budget for Multi-Layer Diagrams:**
For slides with 4+ horizontal layers (like architecture diagrams):
- Title: 0.5" (0.2-0.7")
- Layer 1: 0.8-0.9" (label + components + gap)
- Layer 2: 0.8-0.9"
- Layer 3: 0.8-0.9"
- Layer 4: 0.8-0.9"
- Footer: 0.2-0.3"
- **Total: ~4.5-5.3"** (must stay under 5.625")

**Component Height Guidelines:**
- Small components (5+ per row): 0.4-0.5" tall
- Medium components (3-4 per row): 0.6-0.8" tall
- Large single components: 0.8-1.2" tall
- Layer labels: 0.25-0.3" tall
- Arrows/spacers: 0.15-0.2" tall

**Preventing Overflow:**
1. Calculate total vertical space BEFORE creating shapes
2. Use compressed spacing for dense slides (4+ layers)
3. Abbreviate text labels when needed
4. Test positioning: Last element Y + Height must be < 5.5"
5. If overflow detected, reduce component heights proportionally

### HTML Structure Example

```html
<!DOCTYPE html>
<html>
<head>
<style>
.slide { page-break-after: always; }
.component { 
  display: inline-block; 
  border: 2px solid #0078D4;
  border-radius: 8px;
  padding: 20px;
  margin: 10px;
  background: #E3F2FD;
}
.database {
  border-color: #107C10;
  background: #E8F5E9;
}
</style>
</head>
<body>
<div class="slide">
  <h1>Microservices Architecture</h1>
  <h2>Future State - Member Portal System</h2>
</div>

<div class="slide">
  <h2>High-Level Architecture</h2>
  <div class="component">API Gateway</div>
  <div class="component">Auth Service</div>
  <div class="component">Member Service</div>
  <div class="component database">Member DB</div>
</div>
</body>
</html>
```

### CSS Tips for Diagrams
- Use `position: absolute` for precise placement
- Use `border-radius` for rounded shapes
- Use `border` for component outlines
- Use `background` for fill colors
- Use `::before` and `::after` for arrows (limited support)

## References

### Required Reading
Before creating any diagram:
1. Read `references/arch-patterns.md` for component libraries and patterns
2. Read `references/layout-guide.md` for PowerPoint layout specifics
3. Reference `references/pptx-skill.md` for core PPTX creation workflow

### Pattern Selection Guide
- **Small systems** (< 10 components): Single slide overview
- **Medium systems** (10-30 components): Context + 2-3 architecture slides
- **Large systems** (30+ components): Context + layer slides + detail slides
- **Multi-channel ecosystems**: Channel layer + API layer + services layer + data layer
