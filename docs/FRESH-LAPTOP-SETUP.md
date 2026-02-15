# Fresh Laptop Setup: OpenClaw Analysis

> **Goal:** Set up personal laptop to analyze OpenClaw codebase with Cursor

**Platform:** macOS
**Tools:** Git, Cursor, GitHub CLI (optional)
**Duration:** 15 minutes setup + 2-3 hours analysis

---

## 📋 Prerequisites

Before starting, ensure you have:
- [ ] Personal laptop (NOT work laptop)
- [ ] GitHub account access
- [ ] Cursor IDE installed (download from https://cursor.sh)
- [ ] Git installed (comes with macOS)

---

## 🚀 Step-by-Step Instructions

### **Step 1: Set Up Work Directory**

```bash
# Create your CODE directory
mkdir -p ~/CODE
cd ~/CODE
```

### **Step 2: Clone AAGLOBAL from GitHub**

```bash
# Clone your AAGLOBAL repository
git clone https://github.com/Outtram/AAGLOBAL.git
cd AAGLOBAL

# Verify you have the upgrade docs
ls docs/MAJOR-UPGRADE.md docs/FRESH-LAPTOP-SETUP.md
```

### **Step 3: Clone OpenClaw (Separate, Not in AAGLOBAL)**

```bash
# Go back to CODE directory
cd ~/CODE

# Clone OpenClaw (MIT licensed, open source)
git clone https://github.com/OpenClaw/openclaw.git

# Your directory structure should now be:
# ~/CODE/
#   ├── AAGLOBAL/       # Your project (on GitHub)
#   └── openclaw/       # OpenClaw repo (NOT committed to your GitHub)
```

**Important:** OpenClaw stays OUTSIDE of AAGLOBAL directory! This prevents it from being committed to your GitHub.

### **Step 4: Create Research Folder in AAGLOBAL**

```bash
cd ~/CODE/AAGLOBAL

# Create research folder where Cursor will save analysis
mkdir -p docs/openclaw-research

# This folder WILL be committed to GitHub (your analysis, not OpenClaw code)
```

### **Step 5: Open AAGLOBAL in Cursor**

```bash
# Open AAGLOBAL in Cursor
cd ~/CODE/AAGLOBAL
cursor .
```

**Cursor should open with your AAGLOBAL project.**

### **Step 6: Review .cursorrules**

Cursor will automatically read `.cursorrules` file in AAGLOBAL root. This tells Cursor:
- Where to find OpenClaw (../openclaw/)
- What to analyze
- Where to save analysis docs (docs/openclaw-research/)
- What format to use

**You don't need to do anything - Cursor will follow these rules automatically.**

---

## 🔍 Analysis Phase (In Cursor)

### **Step 7: Start Analysis with Cursor Composer**

In Cursor, open Composer (Cmd+I or click chat icon) and paste:

```
I need you to analyze the OpenClaw codebase at ../openclaw/ and help me understand how to build a safer alternative.

Follow these research questions from docs/MAJOR-UPGRADE.md:

1. MEMORY SYSTEM:
   - How does hybrid search combine SQL + vector embeddings?
   - How does it decide what to remember vs forget?
   - How does SOUL.md personality get stored and recalled?

2. HEARTBEAT:
   - What triggers a notification vs silent check?
   - How does it judge "importance"?
   - How does it avoid alert fatigue?

3. PERSONALITY:
   - How does SOUL.md influence response style?
   - How does it maintain consistent "voice"?
   - How does it make responses feel natural/human?

4. ADAPTERS:
   - How does the gateway pattern work?
   - How does it maintain conversation state across channels?
   - How does it handle async/real-time communication?

5. SESSION CONTINUITY:
   - How does it recall previous conversations?
   - How does it maintain context window efficiently?
   - How does it know when to "forget" old context?

For each topic, create a detailed markdown file in docs/openclaw-research/:
- 01-memory-system.md
- 02-heartbeat-logic.md
- 03-personality-injection.md
- 04-adapter-patterns.md
- 05-session-continuity.md
- 06-human-feel-secrets.md

Include:
- Code examples from OpenClaw
- Architecture diagrams (in markdown/mermaid)
- Key insights about WHY it feels human
- Recommendations for building it safer in AAGLOBAL

Start with the memory system.
```

### **Step 8: Let Cursor Work**

Cursor will:
1. Read the OpenClaw codebase (../openclaw/)
2. Analyze each component
3. Create detailed markdown files in docs/openclaw-research/
4. Explain the architecture and patterns
5. Suggest how to rebuild it securely

**This will take 1-2 hours. Let it run!**

### **Step 9: Review the Analysis**

After Cursor finishes, review the generated files:

```bash
cd ~/CODE/AAGLOBAL/docs/openclaw-research/
ls -la

# You should see:
# 01-memory-system.md
# 02-heartbeat-logic.md
# 03-personality-injection.md
# 04-adapter-patterns.md
# 05-session-continuity.md
# 06-human-feel-secrets.md
# IMPLEMENTATION-PLAN.md (if Cursor created it)
```

### **Step 10: Ask Follow-Up Questions**

In Cursor Composer, ask:

```
Based on your analysis, what are the TOP 3 patterns that make OpenClaw feel "almost human"?

How can we implement these in AAGLOBAL while staying more secure (no public registries, local files only)?

Create an IMPLEMENTATION-PLAN.md with:
1. Priority order (what to build first)
2. Dependencies between components
3. Estimated complexity (simple/medium/complex)
4. Security considerations for each component
```

---

## 💾 Commit Analysis Back to GitHub

### **Step 11: Commit Your Analysis**

```bash
cd ~/CODE/AAGLOBAL

# Check what was created
git status

# Should show:
#   docs/openclaw-research/01-memory-system.md (new)
#   docs/openclaw-research/02-heartbeat-logic.md (new)
#   ... etc

# Add all analysis files
git add docs/openclaw-research/

# Commit with descriptive message
git commit -m "Add OpenClaw analysis from Cursor deep dive

- Memory system architecture and hybrid search
- Heartbeat logic and proactive decision-making
- Personality injection patterns
- Adapter patterns for multi-channel support
- Session continuity and context management
- Human feel secrets and implementation plan"

# Push to GitHub
git push
```

**Important:** This commits ONLY your analysis docs, NOT the OpenClaw codebase!

---

## 🔄 Switch Back to Work Laptop

### **Step 12: Pull Analysis on Work Laptop**

On your work laptop (where Claude Code is running):

```bash
cd /Users/touttram/CODE/AAGLOBAL

# Pull the analysis from GitHub
git pull

# Verify analysis files are there
ls docs/openclaw-research/

# You should see all the markdown files!
```

### **Step 13: Use Analysis with Claude Code**

Now you can ask Claude Code:

```
I've analyzed OpenClaw (see docs/openclaw-research/).

Let's build AAGLOBAL-Brain with these insights:
1. Enhanced memory system (hybrid search)
2. Proactive heartbeat (30-min checks)
3. WhatsApp adapter
4. Gmail/Calendar integration

Start with the memory system. Based on 01-memory-system.md, create:
- .claude/memory/SOUL.md
- .claude/memory/memory.db (SQLite)
- .claude/memory/search.py (hybrid search)
```

---

## 🎯 What You'll Have

After this process:

**On Personal Laptop:**
- ✅ OpenClaw codebase (for reference, not committed)
- ✅ Cursor with full codebase understanding
- ✅ Analysis docs created

**On GitHub:**
- ✅ Your AAGLOBAL project
- ✅ Analysis docs in docs/openclaw-research/
- ✅ Implementation plan

**On Work Laptop:**
- ✅ Analysis docs pulled from GitHub
- ✅ Ready to build with Claude Code
- ✅ Multi-agent setup if needed

---

## 🛠️ Troubleshooting

### **Problem: Can't find OpenClaw repo**

```bash
# Make sure it's cloned OUTSIDE of AAGLOBAL
cd ~/CODE
ls -la

# Should see:
# AAGLOBAL/
# openclaw/

# If openclaw is missing:
git clone https://github.com/OpenClaw/openclaw.git
```

### **Problem: Cursor can't access OpenClaw**

Check .cursorrules in AAGLOBAL root - it should tell Cursor where to find OpenClaw at `../openclaw/`

### **Problem: Analysis files not being created**

Make sure the folder exists:
```bash
cd ~/CODE/AAGLOBAL
mkdir -p docs/openclaw-research/
```

Then ask Cursor to save files explicitly:
```
Save your analysis of the memory system to docs/openclaw-research/01-memory-system.md
```

### **Problem: Git push fails**

```bash
# Check if you're on the right branch
git branch

# Should be on 'main'

# If authentication fails, use GitHub CLI:
gh auth login

# Then try push again
git push
```

---

## 📞 Need Help?

If you get stuck:
1. Check docs/MAJOR-UPGRADE.md for context
2. Read the .cursorrules file to see what Cursor should do
3. Ask Cursor directly: "What should I do next?"
4. Take screenshots and bring them back to work laptop for Claude Code to help

---

## ✅ Checklist

Before switching back to work laptop, verify:

- [ ] OpenClaw cloned at ~/CODE/openclaw/
- [ ] AAGLOBAL cloned at ~/CODE/AAGLOBAL/
- [ ] Analysis files created in docs/openclaw-research/
- [ ] At least 6 markdown files with detailed analysis
- [ ] IMPLEMENTATION-PLAN.md exists
- [ ] All files committed to Git
- [ ] Changes pushed to GitHub
- [ ] You understand the "human feel" secrets!

---

**Good luck! You're about to understand how to build truly intelligent AI agents! 🚀**
