# 06: Human Feel Secrets

## Overview

This is the most important document in the analysis. Everything else is infrastructure — memory, scheduling, adapters. **This is what makes the difference between "useful tool" and "trusted assistant."**

After reading every line of NanoClaw and exploring OpenClaw's architecture, here are the TOP 3 patterns that make these systems feel "almost human."

---

## Secret #1: Conversational Continuity Creates Intimacy

### The Pattern

The agent remembers what you talked about 5 minutes ago, yesterday, and last week. It never asks "what did you mean?" when the context is obvious. It catches up on conversations it missed. It archives what it might forget.

### Why It Works

Humans maintain conversational threads effortlessly. When someone texts you "what about tonight?" you don't need them to specify "dinner tonight, the Italian restaurant we discussed this morning." You just *know*. An agent that does the same feels eerily human.

### How NanoClaw Implements It

**Layer 1 — Session resume:** Every conversation resumes where it left off.

```typescript
// Session ID stored per group, passed to every agent invocation
resume: sessionId,
```

**Layer 2 — Conversation catch-up:** When triggered, the agent gets ALL messages since its last interaction, not just the triggering message.

```typescript
const missedMessages = getMessagesSince(chatJid, sinceTimestamp, ASSISTANT_NAME);
// Agent sees the entire conversation it missed
const prompt = formatMessages(missedMessages);
```

**Layer 3 — Multi-turn keep-alive:** Container stays alive for 30 minutes. Follow-up messages pipe directly into the active session — no cold start, no context reload.

```typescript
if (queue.sendMessage(chatJid, formatted)) {
  // Instant continuation — feels like a live conversation
}
```

**Layer 4 — Pre-compact archiving:** Before context gets compacted, the full transcript is saved as searchable markdown. The agent can always dig into its past.

### How to Copy This

1. **Always pass session ID** when invoking the agent
2. **Always include missed messages** as context (formatted with sender + timestamp)
3. **Keep the agent alive between messages** (30-min idle timeout)
4. **Archive before forgetting** (pre-compact hook)

---

## Secret #2: The Silence Principle — Only Speak When It Matters

### The Pattern

The agent doesn't spam you. It checks email every 30 minutes but only messages when something is genuinely important. It thinks internally but only shows you conclusions. It acknowledges requests quickly but doesn't narrate its work.

### Why It Works

Humans find over-communication annoying. A friend who texts you every 30 minutes with "nothing new!" is not being helpful. But a friend who texts "heads up, your 3pm meeting got moved to 2pm" is invaluable. The difference is **judgement about what matters**.

### How NanoClaw Implements It

**Pattern A — Internal reasoning is hidden:**

```typescript
// From src/router.ts
export function stripInternalTags(text: string): string {
  return text.replace(/<internal>[\s\S]*?<\/internal>/g, '').trim();
}
```

The agent can think out loud inside `<internal>` tags. The user only sees the result. This makes responses feel confident and curated, not stream-of-consciousness.

**Pattern B — Scheduled tasks control their own output:**

From the MCP tool description:

```
MESSAGING BEHAVIOR - The task agent's output is sent to the user or group. 
It can also use send_message for immediate delivery, or wrap output in 
<internal> tags to suppress it. Include guidance in the prompt about whether 
the agent should:
• Always send a message (e.g., reminders, daily briefings)
• Only send a message when there's something to report (e.g., "notify me if...")
• Never send a message (background maintenance tasks)
```

**Pattern C — Scheduled task prefix:**

```typescript
if (containerInput.isScheduledTask) {
  prompt = `[SCHEDULED TASK - The following message was sent automatically 
             and is not coming directly from the user or group.]\n\n${prompt}`;
}
```

This tells the agent it's running autonomously, so it should use judgement about whether to bother the user.

### How OpenClaw Enhances This

OpenClaw's heartbeat has explicit quiet hours and importance judging:

- Skips during quiet hours (sleep time)
- Skips when the request queue is busy (don't interrupt)
- Agent reads a checklist and **decides** what's notification-worthy

### How to Copy This

1. **Implement `<internal>` tag stripping** — let the agent think without showing it
2. **Give tasks explicit messaging guidance** — "only notify if urgent"
3. **Add quiet hours** — no notifications 10pm-7am
4. **Let Claude judge importance** — include context about what's urgent vs routine
5. **Use `send_message` for quick acknowledgement** — then work silently

---

## Secret #3: Channel-Native Communication

### The Pattern

The agent formats its messages for the platform it's on. On WhatsApp, it uses `*bold*` not `**bold**`. It uses bullet points, not headers. It keeps messages short and scannable. It shows "typing..." while thinking. It prefixes its name so you know who's talking in a group.

### Why It Works

Every messaging platform has its own communication norms. A WhatsApp message with `## Headers` and `[links](url)` screams "bot." A message with `*bold*` text, bullet points, and natural flow looks like it was typed by a person. This is the cheapest, highest-impact human-feel improvement.

### How NanoClaw Implements It

**Format enforcement in CLAUDE.md:**

```markdown
## WhatsApp Formatting (and other messaging apps)

Do NOT use markdown headings (##) in WhatsApp messages. Only use:
- *Bold* (single asterisks) (NEVER **double asterisks**)
- _Italic_ (underscores)
- • Bullets (bullet points)
- ```Code blocks``` (triple backticks)

No ## headings. No [links](url). No **double stars**.
```

**Typing indicators:**

```typescript
await whatsapp.setTyping(chatJid, true);    // "Andy is typing..."
const output = await runAgent(/* ... */);
await whatsapp.setTyping(chatJid, false);   // Stop
```

**Name prefix:**

```typescript
// From src/router.ts
export function formatOutbound(channel: Channel, rawText: string): string {
  const text = stripInternalTags(rawText);
  if (!text) return '';
  const prefix = channel.prefixAssistantName !== false 
    ? `${ASSISTANT_NAME}: ` : '';
  return `${prefix}${text}`;
}
```

**Immediate acknowledgement:**

```markdown
You also have `mcp__nanoclaw__send_message` which sends a message immediately 
while you're still working. This is useful when you want to acknowledge a 
request before starting longer work.
```

The agent says "On it!" immediately, then sends the full response when ready. Exactly how a human colleague would respond.

### How to Copy This

1. **Enforce platform-native formatting** — add to system prompt / SOUL.md
2. **Show typing indicators** — simple API call, massive UX improvement
3. **Prefix agent name in group chats** — so it's clear who's talking
4. **Use immediate acknowledgement** — "Working on this..." before long tasks
5. **Keep messages short** — WhatsApp isn't email. 2-3 short paragraphs max.

---

## Bonus Patterns (Honourable Mentions)

### Pattern 4: Self-Scheduling

The agent manages its own schedule through natural conversation:

```
User: "remind me every Friday at 3pm to review tasks"
Agent: *calls schedule_task MCP tool*
Agent: "Done! I'll ping you every Friday at 3pm."
```

No admin panel, no config file. Just talk. This feels like asking a human assistant to set a reminder.

### Pattern 5: Conversation Catch-Up with Sender Context

When the agent is triggered in a group, it sees ALL recent messages with sender names and timestamps:

```xml
<message sender="Troy" time="2026-02-15T14:30:00Z">should we do pizza tonight?</message>
<message sender="Sarah" time="2026-02-15T14:31:00Z">sounds good!</message>
<message sender="Troy" time="2026-02-15T14:32:00Z">@Andy what toppings?</message>
```

The agent understands the conversation flow and responds in context. It knows Troy suggested pizza and Sarah agreed.

### Pattern 6: Graceful Error Recovery

NanoClaw rolls back message cursors on agent errors:

```typescript
if (output === 'error' || hadError) {
  if (outputSentToUser) {
    // Already sent output — don't re-process (would send duplicates)
    return true;
  }
  // Roll back cursor so retries can re-process
  lastAgentTimestamp[chatJid] = previousCursor;
  saveState();
}
```

If the agent crashes mid-response, the message gets re-processed on the next attempt. If the agent already sent a partial response, it doesn't duplicate. Either way, the user's message is never silently lost.

### Pattern 7: Per-Group Identity

Each group can have its own CLAUDE.md, creating subtly different personalities:

- **Main channel**: Full admin access, concise, technical
- **Family group**: Warm, casual, remembers family names
- **Work group**: Professional, action-oriented, deadline-aware

Same agent, different vibes — just like humans adjust their communication style per context.

---

## Summary: What Makes It Feel Human

| Rank | Pattern | Impact | Effort |
|------|---------|--------|--------|
| 1 | **Conversational continuity** (session resume + catch-up + archiving) | Critical | Medium |
| 2 | **Silence principle** (only speak when it matters, hide internal reasoning) | High | Low |
| 3 | **Channel-native formatting** (WhatsApp formatting, typing indicators, name prefix) | High | Low |
| 4 | Self-scheduling via natural language | Medium | Low (use MCP tools) |
| 5 | Conversation catch-up with sender context | Medium | Low |
| 6 | Graceful error recovery | Medium | Medium |
| 7 | Per-group identity | Low | Low |

---

## The Design Philosophy

Both NanoClaw and OpenClaw arrive at the same conclusion from different directions:

> **The best AI assistant is the one you forget is AI.**

NanoClaw achieves this through radical simplicity — small codebase, file-based memory, one channel, container isolation. The "human feel" emerges from good defaults and careful formatting.

OpenClaw achieves this through comprehensive engineering — hybrid search, multi-channel, DM scoping, heartbeat with importance judging. The "human feel" is explicitly designed into every subsystem.

**For AAGLOBAL:** Start with NanoClaw's simplicity. Add OpenClaw's sophistication only where it measurably improves the experience. The biggest wins (formatting, typing indicators, internal tags, session continuity) are all low-effort, high-impact changes.

---

## AAGLOBAL Implementation Priority

1. **Week 1**: Conversational continuity + channel-native formatting
2. **Week 2**: Silence principle (internal tags, quiet hours, importance judging)
3. **Week 3**: Self-scheduling + heartbeat
4. **Week 4**: Polish and edge cases (error recovery, per-group identity)

The "human feel" should be the **first** thing implemented, not the last. Get the UX right before building complex infrastructure.
