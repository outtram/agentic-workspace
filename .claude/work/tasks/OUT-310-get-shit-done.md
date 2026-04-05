---
id: OUT-310
title: Get shit done
type: task
status: todo
priority: low
category: tech
created: '2026-02-28T21:16:01.531208'
updated: '2026-03-23'
branch: task/OUT-310-get-shit-done
source: reminders_import
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
reminder_id: x-apple-reminder://B1507B75-DB1C-498B-8A12-B62F5AEF476F
reminder_list: Reminders
due_date: null
prd: OUT-310
stream_state: seen
last_touched: '2026-03-12T14:59:13'
enriched: true
---

# Get shit done

## Description

🚨 This is how engineers at Amazon, Google, and Shopify actually use Claude Code.

It's called GSD (Get Shit Done) and it solves context rot the quality degradation that destroys your Claude Code sessions as the context window fills up.

No BMAD. No enterprise sprint theater. No Jira nonsense.

Here's how it works:

You run one command
→ /gsd:new-project
→ It interviews you until it fully understands your idea
→ Spawns parallel research agents to investigate your stack
→ Creates atomic task plans with XML structure Claude actually understands
→ Executes in fresh 200k context windows per task
→ Commits every single task to git automatically

Here's the wildest part:

Your main context window stays at 30-40% the entire time.

All the heavy lifting happens in subagent contexts. No degradation. No "I'll be more concise now." Just clean, consistent execution.

Engineers at Amazon, Google, Shopify, and Webflow trust this thing.

MIT license. One command to install:

npx get-shit-done-cc@latest

Link in the first comment 👇

## Steps
- [ ] Clarify the intended outcome and success criteria
- [ ] Review the relevant code, notes, or related tasks
- [ ] Draft the smallest implementation or investigation step
- [ ] Capture findings and the next concrete action
- [ ] Update the task status when the next step is locked in

## Research

Here are 5 actionable findings on GSD:

---

## 1. It's real and actively maintained

GSD ([github.com/glittercowboy/get-shit-done](https://github.com/glittercowboy/get-shit-done)) by TACHES is a legitimate MIT-licensed meta-prompting system. npm package `get-shit-done-cc` is active. It's been forked/ported to OpenCode and Gemini CLI, suggesting genuine adoption.

---

## 2. The core mechanism: subagent isolation per task

Each plan executes in a **fresh 200k context window** via Claude Code subagents. Your main context stays at 30-40% because all heavy lifting (research, planning, execution) runs in child contexts. This maps directly to the `superpowers:subagent-driven-development` skill you already have.

---

## 3. Key slash commands to know

| Command | Purpose |
|---|---|
| `/gsd:new-project` | Interviews you, spawns research agents, builds roadmap |
| `/gsd:discuss-phase N` | Captures decisions before planning |
| `/gsd:plan-phase N` | XML task plan with research baked in |
| `/gsd:execute-phase N` | Runs plans in parallel waves, commits each task |
| `/gsd:verify-work N` | Validates deliverables, auto-diagnoses failures |
| `/gsd:quick` | Skips research/verify for ad-hoc work |

---

## 4. You already have 80% of this

Your AAGLOBAL setup already implements the same patterns:
- Subagent-driven development skill
- Task-per-git-commit workflow
- File-native context (PROJECT.md, REQUIREMENTS.md equivalents)
- Parallel agent dispatching

GSD is a **formalised version** of what you're already doing, with tighter XML structure and automatic verification loops.

---

## 5. Worth installing for one specific gain: `verify-work`

The weakest part of your current setup is **post-execution verification**. GSD's `/gsd:verify-work` auto-diagnoses failures and generates fix plans. That's the most novel piece.

**Next step:**

```bash
npx get-shit-done-cc@latest --claude --local
```

Install locally first (`./.claude/`) to trial on one project before going global. Then compare `/gsd:plan-phase` output quality vs your existing `create-plans` skill.

---

Sources:
- [GitHub - gsd-build/get-shit-done](https://github.com/glittercowboy/get-shit-done)
- [get-shit-done-cc on npm](https://www.npmjs.com/package/get-shit-done-cc)
- [One Codebase, Three Runtimes - Medium](https://medium.com/@richardhightower/one-codebase-three-runtimes-how-gsd-targets-claude-code-opencode-and-gemini-cli-29c98cfe96c6)
- [Hasan Toor original X post](https://x.com/hasantoxr/status/2026268317334524007)

## Note — 2026-03-02 14:14

New note from Troy. My question is should we apply this to this current system or not?

## Progress Log
- 2026-03-23: Enriched in batch review. Preserved existing detail and replaced placeholders where needed.
