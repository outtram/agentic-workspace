---
id: OUT-330
title: kagan.sh
type: task
status: todo
priority: low
created: '2026-03-10T15:47:41.108996'
updated: '2026-03-10T15:47:41.108996'
branch: task/OUT-330-kagan.sh
source: reminders_import
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
reminder_id: x-apple-reminder://4D3EE0E8-1262-405B-8E62-13612F9A7090
reminder_list: Reminders
stream_state: seen
last_touched: '2026-03-11T16:20:26'
---

# kagan.sh

## Description
look into this interesting dev ops ai tool. see if it can help with cc.


## Steps
- [ ] Review task details
- [ ] Complete task
- [ ] Mark as done

## Research

## Kagan.sh — Research Findings

**What it is:** Open-source terminal Kanban board that orchestrates AI coding agents across parallel git worktrees. Install with `uvx kagan`.

---

### 5 Actionable Findings

**1. Claude Code is first-class supported**
Kagan lists CC as a default agent. You can assign it per-task or set it as `default_worker_agent` in config. No special setup needed.

**2. Parallel agents in isolated worktrees**
Each Kagan task runs in its own git worktree — same pattern your superpowers `using-git-worktrees` skill uses. This means you could run 3-4 CC tasks simultaneously without branch conflicts. Big win for your AAGLOBAL multi-task flow.

**3. MCP server with 23+ tools**
Kagan exposes its full board/state via FastMCP. You could control the Kagan board from within a Claude Code session — no need to switch to the TUI. Fits your CLI-preferred workflow.

**4. Review gate before merge**
Every task passes through a mandatory review stage: diff view, acceptance checklist, AI summary → then auto-creates GitHub PR and runs CI. Replaces your manual `gh pr create` steps.

**5. AUTO vs PAIR mode**
- `AUTO` = background execution, you monitor async (good for clear tasks)
- `PAIR` = interactive tmux/neovim session (good for exploratory work)
Mix both on the same board simultaneously.

---

### Next Steps

| Action | Effort |
|--------|--------|
| `uvx kagan` — try it locally, 5 min | Low |
| Wire up your MCP client in CC to the Kagan MCP server | Medium |
| Replace manual `gh pr create` with Kagan's PR automation | Medium |
| Evaluate against your Command Centre TUI for overlap | Low |

**Potential concern:** Your Command Centre TUI is custom-built for AAGLOBAL. Kagan overlaps significantly — worth deciding if you want to run both or integrate selectively via MCP.
