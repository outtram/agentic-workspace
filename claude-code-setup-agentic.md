# Claude Code Setup — Troy's Dev Environment

> Copy this entire file into Claude Code as context when setting up your local environment.
> It contains everything from our planning conversations — architecture decisions, tool choices, workflow patterns, and the Superpowers integration.

---

## 1. WHO I AM (Context for Claude Code)

- **Name:** Troy Outtram
- **Role:** Partner at Deloitte (Big 4 consulting), Melbourne Australia
- **Focus:** Digital transformation in Superannuation / FSI
- **Background:** .NET engineering, learning modern web + AI
- **Conditions:** ADHD + Dyslexia — keep responses short, structured, actionable
- **GitHub:** github.com/Outtram
- **Thinking style:** Phases, deliverables, outcomes. Confirm before executing.

---

## 2. ARCHITECTURE DECISIONS (Already Made)

These are settled. Don't re-debate them.

### Tool Roles
| Tool | Role | Why |
|------|------|-----|
| **Claude Code** | Primary dev agent | Terminal-native, hooks, skills, plugins |
| **GitHub** | Source of truth | All code lives here. CLI for git ops. |
| **Vercel** | Frontend hosting | Auto-deploys from GitHub. Next.js optimised. |
| **Linear** | Project management | Issue tracking, feature specs, status updates |
| **Cloudflare Workers** | API/backend hosting | Free tier, fast, cheap for personal projects |

### CLI vs MCP — The Rule
| Task | Use CLI | Use MCP |
|------|---------|---------|
| Git operations (commit, push, branch) | ✅ | ❌ |
| File operations | ✅ | ❌ |
| Build/test commands | ✅ | ❌ |
| Linear issue management | ❌ | ✅ |
| Structured API integrations | ❌ | ✅ |

**Principle:** CLI for dev work (speed, no overhead, works offline). MCP for structured business workflows (type safety, validation).

### Branching Strategy
- `main` = production (auto-deploys to Vercel)
- `dev` = staging
- `feature/OUT-XX-short-description` = feature branches off `dev`
- Never commit directly to `main`

### Commit Convention
Always prefix with Linear issue ID:
```
OUT-XX: Short description of change
```

---

## 3. INSTALL SUPERPOWERS

Superpowers is an agentic skills framework by Jesse Vincent (obra). It's in the official Anthropic marketplace. 40k+ GitHub stars.

**What it does:** Transforms Claude Code from a code generator into a structured dev workflow — brainstorming → spec → plan → TDD → code review → ship.

### Install in Claude Code
```bash
# In Claude Code CLI:
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### Verify Installation
```bash
# Should show new commands:
/help
# Look for: /superpowers:brainstorm, write-plan, execute-plan
```

### How It Works (7 Phases)
1. **Brainstorm** — Claude asks what you're building before writing code
2. **Spec** — Shows spec in digestible chunks for approval
3. **Plan** — Creates implementation plan clear enough for a junior dev
4. **TDD** — Red/Green/Refactor cycle. Tests BEFORE code. No exceptions.
5. **Subagent Development** — Agents work through tasks with review gates
6. **Code Review** — Two-stage: spec compliance first, then code quality
7. **Finish** — Verify tests, merge options, cleanup

### Key Superpowers Principles
- **YAGNI** — Build simplest thing that works
- **Evidence over claims** — Verify it works before declaring success
- **TDD enforced** — If code written before tests, it gets deleted
- **Subagent isolation** — Tasks run in isolated contexts
- **Automatic skill activation** — Skills trigger based on what you're doing

### Superpowers Slash Commands
| Command | When to Use |
|---------|-------------|
| `/using-superpowers` | Start of session — reminds Claude it has skills |
| `/superpowers:brainstorm` | Starting a new feature |
| `/superpowers:write-plan` | After spec is approved |
| `/superpowers:execute-plan` | Ready to build |

**Always start sessions with `/using-superpowers`** to activate the full skill set.

---

## 4. HOOKS SETUP

Hooks = deterministic actions at specific lifecycle points. Unlike prompts (suggestions), hooks ALWAYS execute.

### Hook Events Available
| Event | When It Fires |
|-------|---------------|
| `PreToolUse` | Before tool calls (can block them) |
| `PostToolUse` | After tool calls (format, lint, test) |
| `Notification` | When Claude needs your attention |
| `PreCompact` | Before context compaction |
| `SessionStart` | When a new session begins |

### Recommended Hooks

#### 1. Desktop Notifications (macOS)
Never miss when Claude needs input:
```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'"
          }
        ]
      }
    ]
  }
}
```

#### 2. Auto-Format After Edits
Run Prettier on every file change:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "write|edit|create",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write \"$FILE_PATH\" 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

#### 3. Date Context on Session Start
Solves the "Claude thinks it's 2024" problem:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\":{\"additionalContext\":\"Today is '$(date '+%A %d %B %Y')'. Timezone: Australia/Melbourne (AEST/AEDT).\"}}'"
          }
        ]
      }
    ]
  }
}
```

### How to Configure Hooks
```bash
# Interactive setup:
/hooks

# Or edit directly:
# User-level: ~/.claude/settings.json
# Project-level: .claude/settings.json (in repo root)
```

**User-level** = applies everywhere. **Project-level** = scoped to that repo.

---

## 5. MEMORY & CONTEXT

### Claude Code Memory (CLAUDE.md)
Create a `CLAUDE.md` file in your project root. Claude Code reads this automatically at session start.

```markdown
# CLAUDE.md — OuttramWebsite

## Project
- Personal website: www.outtram.com
- Stack: Next.js 14 + TypeScript + Tailwind CSS
- Repo: github.com/Outtram/OuttramWebsite
- Hosting: Vercel (auto-deploy from GitHub)
- Project management: Linear (team: Outtram, project: OuttramWebsite)

## Branching
- main = production. Never commit directly.
- dev = staging.
- Feature branches: feature/OUT-XX-short-description
- Always branch off dev.

## Commits
- Prefix with Linear issue ID: "OUT-XX: description"
- Keep commits small and focused.

## Before finishing a feature
- Run all tests
- Update Linear issue status
- Summarise changes in Linear comment

## Code Style
- TypeScript strict mode
- Tailwind for styling (no CSS modules)
- Functional components with hooks
- Keep files under 200 lines where possible

## My Preferences
- Short, direct responses. I have ADHD.
- Confirm before making changes.
- Use CLI for git, not MCP.
- Don't over-engineer. YAGNI.
```

### Personal Memory (~/.claude/CLAUDE.md)
For things that apply across ALL projects:

```markdown
# Global Claude Code Preferences

## Communication
- Keep responses short and actionable
- Use bullet points for steps
- Confirm before executing changes
- Flag confidence level on uncertain decisions

## Dev Patterns
- CLI for git operations (not MCP)
- TDD where practical
- Small commits linked to issues
- Australian English spelling

## Known Context
- Troy is a Partner at Deloitte Melbourne
- .NET background, learning modern web
- Focus: Super/FSI digital transformation
- GitHub: Outtram
- Timezone: Australia/Melbourne
```

---

## 6. AGENTS & SUBAGENTS

### Built-in Code Reviewer (from Superpowers)
Superpowers includes a code-reviewer agent at `agents/code-reviewer.md`. It runs automatically during the execute-plan phase:

1. **Spec Compliance Review** — Does the code match the spec?
2. **Code Quality Review** — Only runs if spec compliance passes
3. **Loop** — Issues found → fix → re-review until clean

### Custom Agents
Place custom agents in `.claude/agents/` in your project:

```markdown
<!-- .claude/agents/linear-updater.md -->
# Linear Updater Agent

You update Linear issues based on completed work.

## Process
1. Read the current issue details from Linear
2. Update status to "Done" or "In Review"
3. Add a comment summarising what changed
4. List key files modified

## Rules
- Never close issues without explicit approval
- Always include the commit hash in the summary
- Use Australian English
```

---

## 7. SKILLS

Skills are reusable instruction sets. Superpowers installs many automatically. You can also create custom ones.

### Custom Skills Location
```
~/.claude/skills/          # Personal skills (all projects)
.claude/skills/            # Project-specific skills
```

### Example Custom Skill
```markdown
<!-- .claude/skills/linear-workflow/SKILL.md -->
# Linear Workflow Skill

When working on a feature:

1. Check Linear for the issue details (use Linear MCP)
2. Create feature branch: `git checkout -b feature/OUT-XX-description`
3. Implement with TDD
4. Commit with prefix: `OUT-XX: description`
5. Push and create PR
6. Update Linear issue status
7. Add summary comment to Linear issue

Always confirm the issue ID before starting work.
```

---

## 8. PROJECT STRUCTURE

### Current Repos
| Repo | Purpose | Stack |
|------|---------|-------|
| OuttramWebsite | Personal site (outtram.com) | Next.js + TS + Tailwind |
| Hevy | Gym workout MCP server | Node.js / Express |
| DeadEyeDarts | Zombie darts game | TBD |
| OrpheusReader | Text-to-speech web app | TBD |
| Book2Audible | TTS for authors | TBD |

### OuttramWebsite Deploy Flow
```
Code in Claude Code
    → git commit (CLI) with OUT-XX prefix
    → git push to GitHub
    → Vercel auto-deploys
        → feature branch = preview URL
        → dev branch = staging
        → main = production (outtram.com)
```

---

## 9. MCP SERVERS TO CONFIGURE

### For Claude Code (if using MCP)
Only add these if you need structured API access:

```json
{
  "mcpServers": {
    "linear": {
      "url": "https://mcp.linear.app/sse"
    }
  }
}
```

**Do NOT add GitHub MCP to Claude Code.** Use `git` and `gh` CLI instead. Less overhead, faster, works offline.

**Do NOT add Vercel MCP to Claude Code.** It exposes 150+ tools and bloats context. Check deploys via `vercel` CLI or vercel.com.

---

## 10. WORKFLOW CHECKLIST

### Starting a New Feature
```
1. Check Linear for issue details
2. /using-superpowers
3. /superpowers:brainstorm (describe what you want)
4. Review and approve the spec
5. /superpowers:write-plan
6. Review and approve the plan
7. /superpowers:execute-plan
8. Review code, tests, and output
9. git add . && git commit -m "OUT-XX: description"
10. git push
11. Check Vercel for preview deploy
12. When ready: merge to dev → test → merge to main
```

### Quick Fix / Bug
```
1. git checkout -b fix/OUT-XX-description
2. Fix the issue (with test if practical)
3. git commit -m "OUT-XX: Fix description"
4. git push
5. Merge to dev, verify, merge to main
```

---

## 11. KEY PHILOSOPHY

From our research into OpenClaw (Peter Steinberger) and enterprise AI patterns:

### What to Steal
- **Conversation-first** — Understand the problem before writing code
- **Human taste in the loop** — One skilled person with taste beats a committee
- **Composable tools** — Simple tools > complex orchestration
- **Ship and learn** — Don't over-plan. Build, test, iterate.
- **CLI army** — Direct tool access beats abstraction layers

### What to Adapt for Enterprise
- Governance IS needed in regulated contexts (APRA, super funds)
- But keep it minimal viable — one role not four
- Test if simpler patterns work before adding complexity
- The 1:4 → 1:100 human-to-AI ratio is the north star

### The Balance
- For personal projects: Steinberger's direct approach wins
- For enterprise: Add governance where compliance requires it
- Always ask: "Am I adding this because it's needed or because it's sellable?"

---

## 12. QUICK REFERENCE

### Essential Commands
```bash
# Start Claude Code
claude

# Start with Superpowers active
# (then type /using-superpowers)

# Git workflow
git checkout -b feature/OUT-XX-description
git add .
git commit -m "OUT-XX: description"
git push -u origin feature/OUT-XX-description

# Check hooks
/hooks

# Install plugins
/plugin marketplace add obra/superpowers
/plugin install superpowers@superpowers
```

### File Locations
```
~/.claude/settings.json     # Global hooks & settings
~/.claude/CLAUDE.md          # Global memory/context
~/.claude/skills/            # Personal skills
~/.claude/agents/            # Personal agents

.claude/settings.json        # Project hooks & settings
CLAUDE.md                    # Project memory/context
.claude/skills/              # Project skills
.claude/agents/              # Project agents
```

### Useful Resources
- Superpowers: github.com/obra/superpowers
- Awesome Claude Code: github.com/hesreallyhim/awesome-claude-code
- Claude Code Hooks Docs: code.claude.com/docs/en/hooks-guide
- Claude Code Plugins: claude.com/blog/claude-code-plugins
- Everything Claude Code: github.com/affaan-m/everything-claude-code
