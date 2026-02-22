---
id: OUT-299
title: "50 days of openclaw learning"
type: task
status: doing
priority: low
created: 2026-02-22
updated: 2026-02-22
assignee: Troy
branch: task/OUT-299-50-days-of-openclaw-learning
source: reminder
reminder_id: "x-apple-reminder://B97811A4-CFBE-4120-87C8-875A1A1BB6B1"
reminder_list: "Reminders"
due_date: ""
eisenhower_quadrant: "q2"
eisenhower_urgent: false
eisenhower_important: true
---

# 50 days of openclaw learning

## Description
Go and read transcripts and get the link to the file that has 20 top tips and look at what we can use please

https://youtu.be/NZ1mKAWJPr4?si=C4eO7ozy8oNR99tP

Get this
https://gist.github.com/velvet-shark/b4c6724c391f612c4de4e9a07b0a74b6

## Steps
- [ ] Watch/read the YouTube video transcript
- [x] Review the gist with 20 top tips
- [x] Identify actionable tips for our workflow
- [x] Document learnings
- [ ] Build /summarize skill (quick win)
- [ ] Add model routing rules to agent configs
- [ ] Create research agent with parallel sub-agents

## Notes
OpenClaw learning resource - looks like a video with practical tips. The gist likely contains a curated list of top tips from the 50-day experience.

## Research Summary (2026-02-22)

Source: https://gist.github.com/velvet-shark/b4c6724c391f612c4de4e9a07b0a74b6

### All 20 OpenClaw Workflows

1. **Morning Twitter Briefing** — Daily timeline scan, curate top 10, save to Obsidian, Discord summary
2. **"Moment Before" E-ink Display** — Wikipedia events → woodcut-style images → TRMNL e-ink
3. **Self-Maintenance: Updates & Backups** — Cron: 4am package update, 4:30am backup configs to GitHub
4. **Background Health Checks** — Every 30min: email scan, calendar check, service health via Coolify
5. **Research Agent with Parallel Sub-agents** — Simultaneous search across Twitter/Reddit/HN/YouTube/blogs
6. **Content Machine: YouTube Stats** — YouTube Analytics API, natural language queries, trend flagging
7. **Web Summaries: /summarize Command** — Structured summaries from any URL (articles, videos, PDFs)
8. **Infrastructure and DevOps** — SSH monitoring, Coolify API, plan-first destructive ops
9. **Coding from Phone** — Describe changes → agent SSHes, edits, commits, pushes PR
10. **Email Triage and Draft Replies** — Classify urgency, draft replies (never send), prompt injection awareness
11. **Calendar and Family Management** — Google Calendar + WhatsApp group, multilingual
12. **Voice Note Transcription** — Whisper transcription across WhatsApp/Telegram/Discord
13. **Daily Life: Coffee Shops, Weather, Reminders** — Google Places, weather, recurring reminders
14. **Helping Friends in Group Chat** — Step-by-step guidance, multilingual, screenshot analysis
15. **Discord Channel Architecture** — 6 channels with model routing (Opus/Sonnet/Haiku)
16. **Discord Bookmarks Replacing Raindrop** — URL → summarise → tag → save to Obsidian
17. **Knowledge Base: Obsidian & QMD Semantic Search** — Embedding index over 2,800+ notes, nightly updates
18. **WordPress Rickroll Honeypot** — Fake /wp-login → rickroll, log IP/agent
19. **Excalidraw Diagrams via MCP** — Architecture diagrams saved to Obsidian
20. **Home Assistant Integration** — Smart home control via REST API with approval gates

### What We Already Do Well
- Self-maintenance/backups (#3) — memory system + git
- Reminders (#13) — Eisenhower matrix system
- File-native tagging (#16) — YAML frontmatter tagging

### High-Value Additions for AAGLOBAL

| # | Tip | How it applies |
|---|-----|---------------|
| **#5** | Research agent with parallel sub-agents | Add a research agent that spawns parallel searches |
| **#7** | /summarize command for any URL | Quick skill — drop URL, get structured summary |
| **#15** | Model routing (Opus/Sonnet/Haiku) | Route by task complexity in agent configs |
| **#17** | Semantic search over notes | QMD index over .claude/memory/ and .claude/work/ |
| **#19** | Excalidraw diagrams via MCP | Architecture diagrams into docs/ |

### Security Best Practices
- Draft-only email — never send directly
- Treat external content as hostile (prompt injection)
- Tailscale everything — private network
- Least privilege integrations
- Approval gates for destructive actions

### Cost Optimisation
- Haiku for monitoring/summaries
- Sonnet for daily assistance/email
- Opus for deep research/complex analysis
- Sub-agents for large tasks to preserve context
- calculator.vlvt.sh for cost estimates

## Source
Imported from macOS Reminders
- Original list: Reminders
- Due date: None
- Priority: 0 (low)

## Progress Log
- 2026-02-22: Imported from Reminders
