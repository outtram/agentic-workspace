---
id: OUT-327
title: System improvements secondary check
type: task
status: todo
priority: low
created: '2026-03-01T21:06:47.844322'
updated: '2026-03-01T21:06:47.844322'
branch: task/OUT-327-system-improvements-secondary-
source: reminders_import
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
reminder_id: x-apple-reminder://0669AA15-2604-4F81-B8A9-E30353452386
reminder_list: Reminders
---

# System improvements secondary check

## Description
Figure out how to get a fresh agent check things out. Read this article. Don't let your AI agent grade its own homework!

Something I've started doing in every AI pipeline I build.

After the main agent finishes its work, I bring in a second one with a completely fresh context.

No memory of what the first agent did. No awareness of the decisions it made. Just: here's the ask <input> and output <outputs>, is it right?

Sounds simple. But it catches things the original agent would never flag.

Because the original agent rationalised its choices as it worked. The reviewer has no choices to defend. It's the same reason you don't ask the person who wrote the code to review it. You ask someone who hasn't seen it yet.

For Example: In our AI-accelerated SDLC, this step sits between design generation and build. An agent produces the detailed design. A fresh one checks it, does this actually match the requirements? Are the integration points consistent? Does anything conflict with what was agreed in discovery?

It's caught wrong numbers, missed fields, made up statements and overstated conclusions - consistently.

Most people treat AI verification as "it looks right to me" or a quick sanity check at the end. That's not the same as a fresh-eyes reviewer with its own clean context window possibly with a different LLM provider.

Build the step in. It's worth it.

## Steps
- [ ] Review task details
- [ ] Complete task
- [ ] Mark as done
