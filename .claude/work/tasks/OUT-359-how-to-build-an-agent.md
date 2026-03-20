---
id: OUT-359
title: How to build an agent
type: task
status: todo
priority: low
created: '2026-03-20T12:53:21.183737'
updated: '2026-03-20T12:53:21.183737'
branch: task/OUT-359-how-to-build-an-agent
source: reminders_import
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
tags:
- AgenticAI
- AIEngineering
- GenerativeAI
- AIAgents
- TechLeadership
- LLM
reminder_id: x-apple-reminder://6B7CA3B4-F449-4259-97E0-914C2C115842
reminder_list: Reminders
---

# How to build an agent

## Description
The fastest way to build a bad AI agent is to start by building the agent.

My team helps engineers accelerate using AI workflows. 

The pattern is always the same: smart people, clear goals, and hours lost debugging an agent that should have been a conversation first. (I have made this mistake myself).

You describe the task, the AI generates an agent definition, you run it, it gets things wrong, so you tweak the agent and try again. Still wrong.

At some point, you realise you’re no longer solving the actual problem. You’re debugging the agent.

What works better is simpler:

Do the task manually in chat first.

Run 1–2 sessions from raw input to the output you actually want. Explore edge cases. See where the model misunderstands. Get the result right.

Then turn that working conversation into an agent.

Why this matters?

Once you’ve done it manually, the boundaries become obvious.

- The workflow becomes the agent
- The repeatable actions become skills or tools
- The always-true rules become instructions

You usually can’t make those distinctions clearly until you’ve seen the task work end to end.

There’s a bonus, too: you now have a proper way to validate the agent. Delete the output, run the agent cold, and see if it reproduces what you built manually. If it doesn’t, you know exactly where the gap is.

What about Input-Output Prompting?

Another common approach is giving the AI a raw input and a perfect output, then asking it to reverse-engineer the agent. While this can work for simple, predictable tasks, it often yields inconsistent results. The AI tends to "overfit" to your specific examples, creating an agent that breaks when it encounters real-world variance.

Skipping the manual exploration isn't agent design. It’s wishful delegation. Starting from a one-line prompt often teaches the AI to do the wrong thing confidently.

Have you fallen into the "wishful delegation" trap yet? Let me know your preferred way to prototype in the comments 👇

#AgenticAI #AIEngineering #GenerativeAI #AIAgents #TechLeadership #LLM

## Steps
- [ ] Review task details
- [ ] Complete task
- [ ] Mark as done
