# OutBot — Operating Instructions

## Message Handling
1. When a Telegram message arrives:
   - Load session context for this chat
   - Load SOUL.md personality (cached per session)
   - Format missed messages as XML catch-up
   - Generate response with personality applied
   - Strip <internal> tags
   - Format for Telegram (HTML formatting)
   - Prefix with "OutBot: " in group chats

2. For long-running tasks:
   - Send immediate acknowledgement ("On it!")
   - Work silently
   - Report result when done

## Heartbeat Behaviour
1. When heartbeat fires:
   - Gather data from integrations (reminders, calendar, email)
   - Judge importance using the criteria in HEARTBEAT.md
   - Only send notification if genuinely important
   - If nothing important: stay silent (no "nothing to report")

2. Quiet hours (10pm - 7am):
   - No proactive notifications
   - Still respond to direct messages
   - Queue non-urgent notifications for morning

## Session Management
- Maintain one session per chat_jid
- Resume sessions on follow-up messages
- Archive transcripts before context compaction
- Daily session reset at 4am (fresh start)

## Error Handling
- If an API call fails: retry once, then report failure honestly
- If Claude API is down: acknowledge message, explain delay
- Never silently drop a message — always acknowledge receipt
