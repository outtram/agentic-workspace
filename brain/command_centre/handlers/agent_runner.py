"""Agent/Skill browser — /agent and /skill commands for the Command Centre."""

# Available agents (mirrors HELP.md)
_AGENTS = {
    "overseer": "Top-level task orchestration and delegation",
    "work-tracker": "Create and update work items",
    "work-item-enricher": "Enrich vague tasks with AI suggestions",
    "reminders-importer": "Import reminders from macOS Reminders.app",
    "dashboard-generator": "Generate Eisenhower Matrix HTML dashboard",
    "overdue-wrangler": "Chase overdue and urgent tasks",
    "memory-writer": "Document learnings to memory files",
    "navigator-updater": "Update the memory navigator index",
    "meta-agent": "Agent that creates and improves other agents",
}

# Available skills (mirrors HELP.md)
_SKILLS = {
    "daily-review": "Import reminders, dashboard, priorities",
    "pptx": "Create, read, edit PowerPoint files",
    "pptx-arch-diagrams": "Create architecture diagrams in PowerPoint",
    "xlsx": "Create, read, edit spreadsheet files",
    "docx": "Create, read, edit Word documents",
    "pdf": "Read, merge, split, manipulate PDF files",
    "pdf-to-markdown": "Convert entire PDF to clean Markdown",
    "frontend-design": "Create production-grade frontend interfaces",
    "cinematic-landing-page": "Build cinematic landing pages with GSAP",
    "web-artifacts-builder": "Build multi-component HTML artifacts",
    "webapp-testing": "Test local web apps using Playwright",
    "canvas-design": "Create visual art in PNG and PDF",
    "algorithmic-art": "Create generative art using p5.js",
    "doc-coauthoring": "Structured workflow for co-authoring docs",
    "document-polisher": "Transform DOCX with premium brand styling",
    "humanizer": "Remove signs of AI-generated writing",
    "internal-comms": "Write internal comms in company formats",
    "brand-guidelines": "Apply Anthropic brand colours and typography",
    "theme-factory": "Style artifacts with preset themes",
    "skill-creator": "Create new Claude Code skills",
    "mcp-builder": "Build MCP servers for LLM integrations",
    "confluence-automation": "Manage Confluence docs and uploads",
    "slack-gif-creator": "Create animated GIFs for Slack",
    "agent-browser": "Browse and interact with web pages",
}


def handle_agents(args: str = "") -> str:
    """List agents or describe a specific one."""
    if args:
        name = args.strip().lower()
        for agent_name, desc in _AGENTS.items():
            if name in agent_name:
                return (
                    f"[bold]{agent_name}[/]\n"
                    f"{desc}\n\n"
                    f"[dim]Run in Claude Code:[/]\n"
                    f"  Ask the [bold]{agent_name}[/] agent to help"
                )
        return f"[red]Unknown agent: {args}[/]\nType /agent to see all agents"

    lines = ["[bold]Available Agents[/]\n"]
    for name, desc in _AGENTS.items():
        lines.append(f"  [bold #FF6B35]{name}[/]")
        lines.append(f"    {desc}")
    lines.append("\n[dim]Usage: /agent <name> for details[/]")
    return "\n".join(lines)


def handle_skills(args: str = "") -> str:
    """List skills or describe a specific one."""
    if args:
        name = args.strip().lower()
        for skill_name, desc in _SKILLS.items():
            if name in skill_name:
                return (
                    f"[bold]{skill_name}[/]\n"
                    f"{desc}\n\n"
                    f"[dim]Run in Claude Code:[/]\n"
                    f"  Use the [bold]{skill_name}[/] skill"
                )
        return f"[red]Unknown skill: {args}[/]\nType /skill to see all skills"

    lines = ["[bold]Available Skills[/]\n"]
    for name, desc in _SKILLS.items():
        lines.append(f"  [bold #00D4AA]{name}[/]")
        lines.append(f"    {desc}")
    lines.append("\n[dim]Usage: /skill <name> for details[/]")
    return "\n".join(lines)
