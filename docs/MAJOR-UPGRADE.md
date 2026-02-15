# AAGLOBAL Major Upgrade: Building the Brain

> **Goal:** Build a safer alternative to OpenClaw with proactive intelligence, integrated into AAGLOBAL

**Timeline:** 3-4 weeks (broken into weekly sprints)
**Approach:** Analyse NanoClaw + OpenClaw → Extract patterns → Rebuild securely

---

## Important Context

**OpenClaw** (github.com/openclaw/openclaw) is 430,000+ lines of TypeScript. Analysing the full thing would take weeks.

**NanoClaw** (github.com/qwibitai/nanoclaw) is ~500 lines and was specifically built as a safer, lighter alternative. It already has:
- WhatsApp integration
- Memory system
- Scheduled jobs (heartbeat)
- Container isolation for security

**Our approach:** Analyse NanoClaw first (primary target, 80% of what we need), then dip into OpenClaw for specific subsystems (memory search, personality injection) if needed.

---

## What We're Building

**"AAGLOBAL-Brain"** - An ultra-personalised AI agent that:

- Remembers everything - Hybrid SQL + vector search memory
- Acts proactively - 30-minute heartbeat checks email/calendar/tasks
- ✅ **Feels human** - Personality-driven responses from SOUL.md
- ✅ **Stays secure** - No public registries, all local files, direct API calls
- ✅ **Multi-channel** - WhatsApp + Terminal + macOS Reminders
- ✅ **Anticipates needs** - Meeting prep, deadline warnings, context-aware

---

## 📋 Phase Breakdown

### **Phase 1: Deep Dive Analysis** (Personal Laptop + Cursor)
**Location:** Personal laptop
**Tool:** Cursor
**Duration:** 2-3 hours

**What to analyze from OpenClaw:**
1. Memory system architecture (hybrid search)
2. Heartbeat logic (proactive decision-making)
3. Personality injection (SOUL.md → responses)
4. Adapter patterns (multi-channel support)
5. Session continuity (context management)
6. **The "human feel" secrets**

**Output:** Detailed markdown docs in `docs/openclaw-research/`

### **Phase 2: Implementation Planning** (Work Laptop + Claude Code)
**Location:** Work laptop
**Tool:** Claude Code
**Duration:** 1 day

**What to build:**
1. Enhanced memory system (`.claude/memory/`)
2. Proactive heartbeat (`.claude/heartbeat/`)
3. WhatsApp adapter (`.claude/adapters/whatsapp/`)
4. API integrations (Gmail, Calendar)
5. Hybrid search (SQL + vector embeddings)

**Output:** Implementation plan with tasks

### **Phase 3: Build & Test** (Work Laptop + Claude Code)
**Location:** Work laptop
**Tool:** Claude Code or multi-agent setup
**Duration:** 1-2 days

**What to implement:**
- Memory system with hybrid search
- Heartbeat with 30-minute cron
- WhatsApp Business API integration
- Gmail/Calendar direct API calls
- Personality-driven responses

**Output:** Working AAGLOBAL-Brain

---

## 🏗️ Architecture Overview

```
AAGLOBAL/
├── .claude/                     # Claude Code context (config, memory, skills)
│   ├── memory/                  # Enhanced memory context files
│   │   ├── SOUL.md              # Your identity, personality, values
│   │   ├── USER.md              # Who Troy is, preferences
│   │   ├── MEMORY.md            # Long-term storage
│   │   ├── AGENTS.md            # Agent behaviours
│   │   └── HEARTBEAT.md         # What to check daily
│   │
│   ├── skills/                  # Local skills (already have, add more)
│   │   ├── daily-review/        # Existing
│   │   ├── content-engine/      # New: Content generation
│   │   └── exec-summary/        # New: Executive summaries
│   │
│   └── reminders/               # Already built!
│
├── brain/                       # Runtime application code (NEW)
│   ├── memory/                  # Hybrid search engine
│   │   ├── memory.db            # SQLite database
│   │   ├── search.py            # Hybrid SQL + vector search
│   │   └── embeddings.py        # FastEmbed integration
│   │
│   ├── heartbeat/               # Proactive intelligence
│   │   ├── beat.py              # Main heartbeat (30-min cron)
│   │   ├── gmail.py             # Gmail API integration
│   │   ├── calendar.py          # Calendar API integration
│   │   ├── reminders.py         # macOS Reminders bridge
│   │   └── judge.py             # Claude judges importance
│   │
│   ├── adapters/                # Multi-channel communication
│   │   ├── whatsapp/            # WhatsApp (see security notes below)
│   │   │   ├── client.py
│   │   │   └── webhook.py
│   │   └── terminal/            # Claude Code (already have!)
│   │
│   ├── requirements.txt         # Python dependencies (vetted)
│   └── pyproject.toml           # Project config
│
└── docs/
    ├── MAJOR-UPGRADE.md         # This file
    ├── FRESH-LAPTOP-SETUP.md    # New laptop instructions
    └── openclaw-research/       # Analysis docs (created by Cursor)
        ├── 01-memory-system.md
        ├── 02-heartbeat-logic.md
        ├── 03-personality-injection.md
        ├── 04-adapter-patterns.md
        ├── 05-human-feel-secrets.md
        └── IMPLEMENTATION-PLAN.md
```

**Why `brain/` is separate from `.claude/`:**
- `.claude/` = Claude Code context files (memory, skills, config)
- `brain/` = Runtime application code (services, APIs, databases)
- Keeps concerns separated and avoids polluting Claude Code's config directory

---

## 🔐 Security Principles

**What makes this SAFER than OpenClaw:**

| Component | OpenClaw | AAGLOBAL-Brain (Safer) |
|-----------|----------|------------------------|
| **Skills** | 5,700+ public registry (230+ malicious!) | Local `.claude/skills/` only |
| **Memory** | Cloud vector DB | Local SQLite + FastEmbed |
| **APIs** | Gateway middleware | Direct API calls (Gmail, Calendar, WhatsApp) |
| **Dependencies** | npm packages (supply chain risk) | Minimal, vetted dependencies |
| **Updates** | Auto-update from registry | Manual, reviewed updates only |

---

## Integration Preferences

**What Troy Wants:**
- WhatsApp - Proactive notifications, conversational interface
- macOS Reminders - Already integrated!
- Gmail - Check important emails (direct API)
- Calendar - Meeting prep notifications (direct API)

**What Troy DOESN'T Need:**
- Asana, Slack, Discord, Telegram

---

## Honest Security Notes

### WhatsApp is NOT "local only"

WhatsApp Business API requires:
1. **Meta Business account** (verified)
2. **Public webhook URL** (to receive messages)
3. **Hosted server** (Cloudflare Tunnel, Railway, or similar)
4. **Costs money** per conversation

This contradicts "no middleware" but it's the reality. Options:
- **Option A:** WhatsApp Business API (official, requires hosting)
- **Option B:** WhatsApp Web automation (unofficial, fragile, could break)
- **Option C:** NanoClaw's approach (container-isolated agents with WhatsApp)

NanoClaw's container approach is worth studying here.

### API Credentials Required

| Service | What You Need | Where to Get It |
|---------|---------------|-----------------|
| Gmail | OAuth 2.0 credentials | Google Cloud Console |
| Calendar | Same OAuth (bundled with Gmail) | Google Cloud Console |
| WhatsApp | Business API token + webhook | Meta Business Suite |

**Store credentials in:**
- `.env` file (already in .gitignore)
- NEVER commit to Git

### Dependency Management

```bash
# Create virtual environment
python3 -m venv brain/.venv
source brain/.venv/bin/activate

# Install from requirements.txt (vetted deps only)
pip install -r brain/requirements.txt
```

---

## 📚 Research Questions for Cursor

When analyzing OpenClaw codebase, focus on:

1. **Memory System:**
   - How does hybrid search combine SQL + vector embeddings?
   - How does it decide what to remember vs forget?
   - How does SOUL.md personality get stored and recalled?

2. **Heartbeat:**
   - What triggers a notification vs silent check?
   - How does it judge "importance"?
   - How does it avoid alert fatigue?

3. **Personality:**
   - How does SOUL.md influence response style?
   - How does it maintain consistent "voice"?
   - How does it make responses feel natural/human?

4. **Adapters:**
   - How does the gateway pattern work?
   - How does it maintain conversation state across channels?
   - How does it handle async/real-time communication?

5. **Session Continuity:**
   - How does it recall previous conversations?
   - How does it maintain context window efficiently?
   - How does it know when to "forget" old context?

---

## 📝 Next Steps

### **Step 1: Commit This Plan**
```bash
git add docs/MAJOR-UPGRADE.md docs/FRESH-LAPTOP-SETUP.md .cursorrules
git commit -m "Add major upgrade plan for AAGLOBAL-Brain"
git push
```

### **Step 2: Switch to Personal Laptop**
Follow instructions in `docs/FRESH-LAPTOP-SETUP.md`

### **Step 3: Analyze OpenClaw with Cursor**
Cursor will auto-create analysis docs in `docs/openclaw-research/`

### **Step 4: Bring Analysis Back**
```bash
git add docs/openclaw-research/
git commit -m "Add OpenClaw analysis and implementation plan"
git push
```

### **Step 5: Switch Back to Work Laptop**
```bash
git pull
# Analysis is now available for Claude Code to implement!
```

---

## 🎓 Learning Goals

By the end of this upgrade, you'll understand:

- ✅ How to build proactive AI that anticipates needs
- ✅ How hybrid search makes memory feel natural
- ✅ How personality injection makes responses human
- ✅ How to integrate multiple channels securely
- ✅ How to avoid supply chain attacks in AI agents

---

## 💡 Tips

- **Take your time on Phase 1** - Understanding WHY it feels human is key
- **Document everything** - Your future self will thank you
- **Test incrementally** - Build one component at a time
- **Stay secure** - No public registries, review all dependencies
- **Keep it simple** - Start with core features, add more later

---

## 📞 Support

If you get stuck:
1. Check `docs/FRESH-LAPTOP-SETUP.md` for detailed instructions
2. Review `docs/openclaw-research/` for analysis insights
3. Ask Claude Code to explain specific components
4. Use multi-agent setup for parallel implementation

---

**Let's build something amazing! 🚀**
