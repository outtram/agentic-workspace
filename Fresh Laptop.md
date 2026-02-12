# Fresh Laptop Setup Guide

> Set up agentic-workspace on a new Mac with full context, memory, and automation

## 🎯 What You'll Get

- All agents (reminders-importer, dashboard-generator, memory-writer, etc.)
- Complete memory system (skills, decisions, patterns from all projects)
- Work tracking (PRDs, bugs, tasks)
- CLAUDE.md with your preferences and workflows
- `/daily-review` skill and conversational triggers
- Quick access via `workspace` alias

---

## 📋 Prerequisites

- macOS
- Claude Code CLI installed
- GitHub CLI (`gh`) installed
- Git configured with your credentials
- Python 3 (for reminders import scripts)

---

## 🚀 Setup Steps

### 1. Clone the Repository

```bash
# Navigate to where you keep code projects
cd ~/CODE  # or wherever you prefer

# Clone the agentic-workspace repo
git clone https://github.com/outtram/agentic-workspace.git

# Enter the directory
cd agentic-workspace

# Verify CLAUDE.md exists
ls -la CLAUDE.md
```

**Expected output:** You should see CLAUDE.md, .claude/ directory, and other files

---

### 2. Authenticate GitHub CLI (for gist updates)

```bash
# Login to GitHub CLI
gh auth login

# Follow the prompts:
# - Select: GitHub.com
# - Protocol: HTTPS
# - Authenticate: via web browser
# - Paste the one-time code when prompted
```

**Test it works:**
```bash
gh auth status
# Should show: ✓ Logged in to github.com as outtram
```

---

### 3. Set Up Workspace Alias

Add this to your shell config file:

**For zsh (macOS default):**
```bash
# Open your shell config
nano ~/.zshrc

# Add this line at the end:
alias workspace="cd /Users/touttram/CODE/agentic-workspace && claude"

# Save (Ctrl+O, Enter, Ctrl+X)

# Reload your shell config
source ~/.zshrc
```

**For bash (older Macs):**
```bash
# Open your shell config
nano ~/.bash_profile

# Add the same alias line
alias workspace="cd /Users/touttram/CODE/agentic-workspace && claude"

# Save and reload
source ~/.bash_profile
```

**Note:** Adjust the path `/Users/touttram/CODE/agentic-workspace` if you cloned it elsewhere!

---

### 4. Test the Setup

```bash
# From any directory, type:
workspace

# Claude Code should start in the agentic-workspace directory
# You should see the project context loaded
```

**Verify in Claude Code:**
- Say: "show me my memory structure"
- Expected: Claude should reference .claude/memory/NAVIGATOR.md
- Say: "what skills do I have?"
- Expected: Claude should mention /daily-review and other skills

---

## 🔄 Daily Workflow

### Morning Routine

From **any directory**, just type:
```bash
workspace
```

Then in Claude Code, say any of:
- `"do my daily review"`
- `/daily-review`
- `"import my reminders"`
- `"show me my Q1 tasks"`

Claude will:
1. Import active reminders from macOS Reminders
2. Generate Eisenhower Matrix dashboard
3. Update mobile gist automatically
4. Show your top Q1 priorities

---

### Keeping Memory Synced

**When you finish work on Laptop 1:**
```bash
# Commit any work item updates
git add .claude/work/tasks/*.md
git add .claude/memory/*.yml  # if you updated memory
git commit -m "Daily work updates"
git push
```

**When you start work on Laptop 2:**
```bash
workspace

# In Claude Code:
"pull latest updates"
```

Or manually:
```bash
cd /Users/touttram/CODE/agentic-workspace
git pull
claude
```

---

## 📱 Mobile Dashboard Setup

Your Eisenhower Matrix is accessible on mobile via a permanent URL:

**Permanent URL:**
```
https://gist.githack.com/outtram/20f5befb1e2f8cef427b784e6860ddf8/raw/eisenhower-dashboard.html
```

**Add to iPhone Home Screen:**
1. Open the URL in Safari on your iPhone
2. Tap the Share button (square with arrow)
3. Scroll down and tap "Add to Home Screen"
4. Name it: "Eisenhower" or "Q1 Tasks"
5. Tap "Add"

**Auto-Updates:**
- Every time you run `/daily-review` on any laptop
- Dashboard generator automatically updates the gist
- Mobile URL stays the same, content refreshes
- No manual sync needed!

---

## 🧠 How Memory Works Across Devices

### What Syncs (in GitHub):
- ✅ `.claude/memory/` - All skills, decisions, patterns, projects
- ✅ `.claude/agents/` - All specialized agents
- ✅ `.claude/config/` - Configuration files
- ✅ `.claude/templates/` - HTML templates
- ✅ `.claude/dashboards/` - Generated dashboard snapshots
- ✅ `CLAUDE.md` - Your preferences and workflows
- ✅ Work items you commit (PRDs, bugs, tasks)

### What Stays Local (gitignored):
- ❌ `.claude/settings.local.json` - Personal Claude Code settings
- ❌ Test data (OUT-220 to OUT-236)
- ❌ Temporary workspace files

**Result:** Your "brain" travels with you, but each laptop has its own local settings.

---

## 🛠️ Troubleshooting

### "Permission denied" when running scripts

```bash
chmod +x .claude/scripts/*.py
```

### Alias doesn't work

```bash
# Check if it's in your config
grep workspace ~/.zshrc

# If missing, add it:
echo 'alias workspace="cd /Users/touttram/CODE/agentic-workspace && claude"' >> ~/.zshrc
source ~/.zshrc
```

### Memory not loading

```bash
# Verify you're in the right directory
pwd
# Should show: /Users/touttram/CODE/agentic-workspace

# Check CLAUDE.md exists
ls -la CLAUDE.md

# Restart Claude Code
exit
workspace
```

### Git push fails

```bash
# Check remote is configured
git remote -v
# Should show: origin https://github.com/outtram/agentic-workspace.git

# Re-authenticate GitHub CLI
gh auth setup-git
```

---

## 📊 Quick Reference

| Task | Command |
|------|---------|
| Start workspace | `workspace` |
| Daily review | "do my daily review" or `/daily-review` |
| Show priorities | "show me my Q1 tasks" |
| Import reminders | "import my reminders" |
| Pull updates | `git pull` (before starting) |
| Push updates | `git push` (after changes) |
| View memory | `cat .claude/memory/NAVIGATOR.md` |
| Mobile dashboard | Open saved home screen icon |

---

## 🎓 Learning Resources

- **CLAUDE.md** - Your preferences and workflows
- **NAVIGATOR.md** - Grep patterns for finding everything
- **.claude/agents/** - Documentation for each agent
- **.claude/skills/** - Documentation for each skill
- **Fresh Laptop.md** - This file!

---

## ✅ Verification Checklist

After setup, verify:

- [ ] `workspace` command launches Claude Code
- [ ] Claude recognises CLAUDE.md context
- [ ] `/daily-review` skill is available
- [ ] "do my daily review" triggers import workflow
- [ ] Memory files are accessible in `.claude/memory/`
- [ ] `git pull` and `git push` work without errors
- [ ] Mobile dashboard URL loads on phone
- [ ] Python scripts are executable

---

## 🚀 You're All Set!

Your agentic-workspace is now portable across all your devices. The memory compounds over time - every project makes Claude smarter for the next one.

**Questions?** Just ask Claude in the workspace: "How do I [thing you want to do]?"

---

**Last updated:** 2026-02-12
**Repository:** https://github.com/outtram/agentic-workspace
**Mobile Dashboard:** https://gist.githack.com/outtram/20f5befb1e2f8cef427b784e6860ddf8/raw/eisenhower-dashboard.html
