---
id: OUT-340
title: GitHub pr needed
type: task
status: todo
priority: medium
created: '2026-03-10T20:01:31.677155'
updated: '2026-03-10T20:01:48.512160'
branch: task/OUT-340-github-pr-needed
source: email
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
reminder_id: x-apple-reminder://1FC96319-E4E7-4E7F-ABB7-48ABD02A9275
reminder_list: Reminders
---

# GitHub pr needed

## Description
From: Troy Outtram
gh pr create \
--base main \
--head claude/explore-project-automation-BrhQG \
--title "Add project automation agents and enrich work item backlog" \
--body "## Summary
- 4 new agents: enricher, wrangler, overseer, meta-agent
- 14 work items enriched with real steps, categories, Eisenhower fixes
- 7 overdue items wrangled (3 escalated, 2 reclassified, 2 clarified)
- 5 done OutBot tasks moved to done/ folder
- NAVIGATOR.md updated with agent registry and pipelines

## Steps
- [ ] Review task details
- [ ] Complete task
- [ ] Mark as done
