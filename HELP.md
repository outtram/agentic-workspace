# AAGLOBAL Help

## Terminal Commands (available from anywhere)

| Command | What it does |
|---------|-------------|
| `cc` | Command Centre TUI — 3x3 tile grid with multi-select, today list, pagination |
| `outbot` | OutBot text chat (Opus 4.6) |
| `outbot voice` | OutBot voice chat |
| `outbot sonnet` | OutBot using Sonnet (cheaper) |
| `outbot haiku` | OutBot using Haiku (cheapest) |
| `outbot opus` | OutBot using Opus (explicit) |
| `outbot test` | Run OutBot diagnostics |
| `outbot debug` | OutBot with debug logging |
| `claude` | Claude Code CLI |
| `cursor-agent` | Cursor agent CLI |

## Command Centre Keybindings (inside `cc`)

| Key | Action |
|-----|--------|
| Arrow keys | Move focus between tiles |
| 1-9 | Jump to tile by position |
| Space / Enter | Toggle select on focused tile |
| a | Select all on page |
| n | Deselect all |
| t | Add selected (or focused) to today |
| d | Mark done (local + iOS) |
| e | Edit focused task (opens modal) |
| [ / ] | Page left / right |
| / | Focus command bar (slash commands) |
| : | Focus command bar (filters — :q1, :overdue, :today, :search) |
| ? | Show help overlay |
| Escape | Clear selection → clear filter → close response → double-tap to quit |

### Command Centre Slash Commands (inside `cc` command bar)

| Command | What it does |
|---------|-------------|
| `/done` | Mark selected tasks done (local + iOS + git) |
| `/today` | Add selected to today list |
| `/remove` | Remove selected from today list |
| `/q1` .. `/q4` | Move selected to Eisenhower quadrant |
| `/enrich` | Improve task descriptions via Claude |
| `/daily` | Run daily review pipeline |
| `/help` | Show available commands |

## Slash Commands (inside Claude Code)

| Command | What it does |
|---------|-------------|
| `/daily-review` | Import reminders, generate Eisenhower dashboard, show Q1 priorities |
| `/using-superpowers` | Load the superpowers workflow for skills-driven development |
| `/debug` | Apply expert debugging methodology to investigate a specific issue |
| `/check-todos` | List outstanding todos and select one to work on |
| `/add-to-todos` | Add todo item to TO-DOS.md with context from conversation |
| `/whats-next` | Create a handoff document for continuing work in a fresh context |
| `/create-plan` | Create hierarchical project plans for solo agentic development |
| `/run-plan` | Execute a PLAN.md file directly without loading planning skill context |
| `/create-agent-skill` | Create or edit Claude Code skills with expert guidance |
| `/create-subagent` | Create specialised Claude Code subagents |
| `/create-slash-command` | Create a new slash command following best practices |
| `/create-hook` | Expert guidance on Claude Code hook development |
| `/create-prompt` | Create a new prompt that another Claude can execute |
| `/run-prompt` | Delegate prompts to fresh sub-task contexts |
| `/create-meta-prompt` | Create optimised prompts for Claude-to-Claude pipelines |
| `/audit-skill` | Audit a skill for YAML compliance and best practices |
| `/audit-subagent` | Audit subagent configuration for role definition and prompt quality |
| `/audit-slash-command` | Audit slash command file for structure and content quality |
| `/heal-skill` | Heal skill documentation by applying corrections |
| `/consider:first-principles` | Break down to fundamentals and rebuild from base truths |
| `/consider:10-10-10` | Evaluate decisions across three time horizons |
| `/consider:swot` | Map strengths, weaknesses, opportunities, and threats |
| `/consider:one-thing` | Identify the single highest-leverage action |
| `/consider:occams-razor` | Find simplest explanation that fits all the facts |
| `/consider:5-whys` | Drill to root cause by asking why repeatedly |
| `/consider:second-order` | Think through consequences of consequences |
| `/consider:eisenhower-matrix` | Apply Eisenhower matrix to prioritise tasks or decisions |
| `/consider:opportunity-cost` | Analyse what you give up by choosing this option |
| `/consider:via-negativa` | Improve by removing rather than adding |
| `/consider:inversion` | Solve problems backwards — what would guarantee failure? |
| `/consider:pareto` | Apply Pareto's principle (80/20 rule) to current discussion |

## Reminders CLI (from project root)

| Command | What it does |
|---------|-------------|
| `cd .claude/reminders && python3 -m reminders.plugins.cli sync` | Pull reminders from iOS and create work items |
| `cd .claude/reminders && python3 -m reminders.plugins.cli list` | List all active reminders |
| `cd .claude/reminders && python3 -m reminders.plugins.cli show OUT-XXX` | Show detailed info for a task |
| `cd .claude/reminders && python3 -m reminders.plugins.cli add "title"` | Create a new reminder (syncs to iOS) |
| `cd .claude/reminders && python3 -m reminders.plugins.cli complete OUT-XXX` | Mark a task as done (syncs to iOS) |
| `cd .claude/reminders && python3 -m reminders.plugins.cli delete OUT-XXX` | Delete a reminder from both systems |
| `cd .claude/reminders && python3 -m reminders.plugins.cli enrich OUT-XXX` | Make a vague task more actionable with AI |
| `cd .claude/reminders && python3 -m reminders.plugins.cli nudge` | Check for overdue and urgent tasks |
| `cd .claude/reminders && python3 -m reminders.plugins.cli progress` | Help complete the next step of a task |

## Agents (available inside Claude Code)

| Agent | What it does |
|-------|-------------|
| overseer | Top-level task orchestration and delegation |
| work-tracker | Create and update work items |
| work-item-enricher | Enrich vague tasks with AI suggestions |
| reminders-importer | Import reminders from macOS Reminders.app |
| dashboard-generator | Generate Eisenhower Matrix HTML dashboard |
| overdue-wrangler | Chase overdue and urgent tasks |
| memory-writer | Document learnings to memory files |
| navigator-updater | Update the memory navigator index |
| meta-agent | Agent that creates and improves other agents |

## Skills (available inside Claude Code)

| Skill | What it does |
|-------|-------------|
| daily-review | Import reminders, dashboard, priorities |
| superpowers | Skills-driven development workflow |
| pptx | Create, read, edit PowerPoint files |
| pptx-arch-diagrams | Create architecture diagrams in PowerPoint |
| xlsx | Create, read, edit spreadsheet files |
| docx | Create, read, edit Word documents |
| pdf | Read, merge, split, manipulate PDF files |
| pdf-to-markdown | Convert entire PDF to clean Markdown |
| frontend-design | Create production-grade frontend interfaces |
| cinematic-landing-page | Build cinematic landing pages with GSAP animations |
| web-artifacts-builder | Build multi-component HTML artifacts |
| webapp-testing | Test local web apps using Playwright |
| canvas-design | Create visual art in PNG and PDF |
| algorithmic-art | Create generative art using p5.js |
| doc-coauthoring | Structured workflow for co-authoring documentation |
| document-polisher | Transform DOCX with premium brand styling |
| humanizer | Remove signs of AI-generated writing |
| internal-comms | Write internal communications in company formats |
| brand-guidelines | Apply Anthropic brand colours and typography |
| theme-factory | Style artifacts with preset themes |
| skill-creator | Create new Claude Code skills |
| mcp-builder | Build MCP servers for LLM integrations |
| confluence-automation | Manage Confluence docs, downloads, uploads |
| slack-gif-creator | Create animated GIFs optimised for Slack |
| agent-browser | Browse and interact with web pages |

## Dashboards

| URL | What it shows |
|-----|---------------|
| https://gist.githack.com/outtram/20f5befb1e2f8cef427b784e6860ddf8/raw/eisenhower-dashboard.html | Mobile Eisenhower dashboard (auto-updates on /daily-review) |
| `open .claude/dashboards/eisenhower-latest.html` | Local Eisenhower dashboard |

## Quick Start

1. `cc` — Command Centre (spatial tile grid)
2. `/daily-review` — full morning review (import, dashboard, priorities)
3. `outbot` — chat with OutBot
