# Parallel Development Optimization Guide

## 🎯 Current Workflow (Optimized)

### Starting a New Story

**Each dev session**:
```
execute devX_tier5.md
```

**No need to /clear first** - The file contains all necessary context.

### Completing a Story

**Option A: Automated (Recommended)**

Tell each dev:
```
Run this command when done:
./complete-story.sh <story-id> <dev-num> <branch-name>

Example:
./complete-story.sh 2-5 1 story-2-5-input-files
```

This automatically:
- ✅ Updates sprint-status.yaml
- ✅ Runs all tests
- ✅ Commits with proper message
- ✅ Merges to main
- ✅ Pushes to remote

**Option B: Manual (Current)**

Follow the 5-step workflow in devX_tier5.md files.

---

## ⚡ Optimization Suggestions

### 1. **Session Management** ✅ Do This

**Should you /clear before each story?**

**Answer**: Optional, but recommended for these reasons:

| /clear Before Story | Benefits | Drawbacks |
|---------------------|----------|-----------|
| ✅ **YES** | - Fresh context<br>- Reduced token usage<br>- No confusion from previous story | - Loses conversation history<br>- Can't reference previous work |
| ❌ **NO** | - Can reference previous story<br>- Continuity across stories | - Higher token usage<br>- Potential context confusion |

**Best Practice**:
- **DO /clear** between stories (Wave 2 → Wave 3)
- **DON'T /clear** during a story (mid-implementation)

**Optimal Flow**:
```
Wave 2: execute dev1_tier5.md
  ... dev works ...
  ./complete-story.sh 2-5 1 story-2-5-input-files

[Dev says "Story 2-5 merged"]

/clear                    ← Clear context
Wave 3: execute dev1_tier5.md    ← Fresh start
```

---

### 2. **Merge Order Coordination** ⭐ Prevents Conflicts

**Problem**: If 3 devs merge simultaneously, conflicts happen.

**Solution**: Merge in order (first done, first merged)

**Add to completion script**:
```bash
# Lock file prevents simultaneous merges
LOCK_FILE=".git/merge.lock"

acquire_lock() {
    while [ -f "$LOCK_FILE" ]; do
        echo "⏳ Waiting for other dev to finish merging..."
        sleep 2
    done
    touch "$LOCK_FILE"
}

release_lock() {
    rm -f "$LOCK_FILE"
}

# In merge section:
acquire_lock
git merge "$BRANCH_NAME"
git push origin main
release_lock
```

---

### 3. **Parallel Test Execution** 🚀 Faster Feedback

**Problem**: Running full test suite (138 tests) takes time.

**Solution**: Each dev runs only their story's tests first, full suite at merge.

**Add to devX_tier5.md**:
```bash
# Quick test (during development)
venv/bin/pytest tests/unit/test_your_story.py tests/integration/test_your_story.py -v

# Full test (before merge)
venv/bin/pytest tests/ -v
```

**Benefit**:
- Quick feedback: 30s → 2s
- Full validation still happens pre-merge

---

### 4. **Automated Story Assignment** 📋 Eliminate Manual Files

**Problem**: Manually updating 3 devX_tier5.md files for each wave.

**Solution**: Single config file + generator script.

**Create**: `tier5-stories.yaml`
```yaml
wave_3:
  dev1:
    story_id: 7-5
    title: --remote-only Flag
    epic: 7
    estimate: 2-4h
    branch: story-7-5-remote-only-flag

  dev2:
    story_id: 5-4
    title: Organize Batch Outputs
    epic: 5
    estimate: 4-6h
    branch: story-5-4-batch-output-organization

  dev3:
    story_id: 6-3
    title: Cache Invalidation
    epic: 6
    estimate: 4-6h
    branch: story-6-3-cache-invalidation
```

**Generate prompts**:
```bash
./generate-dev-prompts.sh wave_3
# Outputs: dev1_tier5.md, dev2_tier5.md, dev3_tier5.md
```

**Benefit**: Update one file, regenerate all 3 prompts automatically.

---

### 5. **Status Dashboard** 📊 Real-Time Visibility

**Problem**: Hard to see overall progress across 3 devs.

**Solution**: Quick status command.

**Add to repo**:
```bash
#!/bin/bash
# status.sh - Show current wave status

echo "📊 Tier 5 Wave Status"
echo ""

# Show in-progress stories
echo "🔵 In Progress:"
grep "in-progress" docs/sprint-artifacts/sprint-status.yaml | head -3

echo ""

# Show completed today
echo "✅ Completed Today:"
grep "COMPLETED $(date +%Y-%m-%d)" docs/sprint-artifacts/sprint-status.yaml

echo ""

# Show branches
echo "🌿 Active Branches:"
git branch | grep "story-"

echo ""

# Show recent commits
echo "💾 Recent Commits (last 3):"
git log --oneline -3
```

**Usage**:
```bash
./status.sh
```

**Output**:
```
📊 Tier 5 Wave Status

🔵 In Progress:
  2-5-handle-script-input-files-as-arguments: in-progress  # Dev 1
  5-3-track-batch-execution-progress: in-progress  # Dev 2
  6-2-implement-dependency-layer-caching: in-progress  # Dev 3

✅ Completed Today:
  7-2-auto-collect-output-files-from-container: done  # COMPLETED 2025-11-16
  7-3-store-outputs-in-minio-with-retention-policy: done  # COMPLETED 2025-11-16

🌿 Active Branches:
  story-2-5-input-files
  story-5-3-batch-progress
  story-6-2-dependency-caching

💾 Recent Commits (last 3):
  516bac2 Mark Story 7-2 as done
  6fab092 Fix test regressions
  0563940 Complete Tier 4
```

---

### 6. **Pre-Commit Hook Enhancement** 🛡️ Prevent Bad Merges

**Add to** `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Enhanced pre-commit hook

# 1. Run tests
echo "Running tests..."
if ! venv/bin/pytest tests/ -v --tb=short; then
    echo "❌ Tests failed. Commit blocked."
    exit 1
fi

# 2. Check sprint status updated
if git diff --cached --name-only | grep -q "\.py$"; then
    if ! git diff --cached docs/sprint-artifacts/sprint-status.yaml | grep -q "done"; then
        echo "⚠️  Warning: Code changed but sprint-status.yaml not updated to 'done'"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# 3. Check for merge conflicts
if git diff --cached | grep -q "^<<<<<<<"; then
    echo "❌ Merge conflict markers detected. Resolve before committing."
    exit 1
fi

echo "✅ Pre-commit checks passed"
```

---

### 7. **Notification System** 🔔 Know When Devs Finish

**Problem**: Polling to see if devs are done.

**Solution**: Devs auto-notify on completion.

**Add to complete-story.sh**:
```bash
# At the end
echo ""
echo "🔔 NOTIFICATION: Story $STORY_ID completed by Dev $DEV_NUM"
echo "   Ready for Wave $(( $(echo $STORY_ID | cut -d- -f1) + 1 ))"
echo ""

# Optional: Send desktop notification (macOS)
# osascript -e 'display notification "Story '$STORY_ID' complete!" with title "RGrid Dev '$DEV_NUM'"'

# Optional: Send to Slack/Discord webhook
# curl -X POST $WEBHOOK_URL -d '{"text":"Story '$STORY_ID' complete!"}'
```

---

## 📋 Recommended Optimized Workflow

### Setup (Once)
```bash
chmod +x complete-story.sh
chmod +x status.sh
```

### Per Wave

**Start Wave**:
```bash
# Terminal 1 (Dev 1)
/clear
execute dev1_tier5.md

# Terminal 2 (Dev 2)
/clear
execute dev2_tier5.md

# Terminal 3 (Dev 3)
/clear
execute dev3_tier5.md
```

**Monitor Progress**:
```bash
# In main terminal
watch -n 10 ./status.sh  # Updates every 10 seconds
```

**When Dev Finishes** (they run this):
```bash
./complete-story.sh <story-id> <dev-num> <branch-name>
```

**Between Waves**:
```bash
# In each dev session
/clear              # Fresh context
execute devX_tier5.md    # Next wave auto-loaded
```

---

## 🎯 Summary: Top 3 Optimizations

### 1. ✅ **Use /clear between waves** (not during stories)
- Reduces token usage
- Fresh context for each story
- Prevents confusion

### 2. ✅ **Use complete-story.sh script**
- Automates 5-step workflow
- Runs tests automatically
- Consistent commit messages

### 3. ✅ **Add merge lock to prevent conflicts**
- First done, first merged
- Eliminates simultaneous merge conflicts
- Clean git history

---

## 💡 Quick Wins (Implement These First)

1. **Start using complete-story.sh** for Wave 2 completions (already created ✅)
2. **Run /clear before starting Wave 3**
3. **Add merge lock to complete-story.sh**
4. **Create status.sh for visibility**

These 4 changes will make your parallel dev flow much smoother!

---

**Questions? Try**: `/help` or check BMAD docs
