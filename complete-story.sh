#!/bin/bash
# complete-story.sh - Automates story completion workflow
# Usage: ./complete-story.sh <story-id> <dev-number> <branch-name>
# Example: ./complete-story.sh 2-5 1 story-2-5-input-files

set -e  # Exit on error

STORY_ID=$1
DEV_NUM=$2
BRANCH_NAME=$3

if [ -z "$STORY_ID" ] || [ -z "$DEV_NUM" ] || [ -z "$BRANCH_NAME" ]; then
    echo "Usage: ./complete-story.sh <story-id> <dev-number> <branch-name>"
    echo "Example: ./complete-story.sh 2-5 1 story-2-5-input-files"
    exit 1
fi

echo "🎯 Completing Story $STORY_ID (Dev $DEV_NUM)..."

# 1. Update sprint status
echo "📝 Updating sprint-status.yaml..."
STORY_LINE=$(grep -n "$STORY_ID" docs/sprint-artifacts/sprint-status.yaml | head -1 | cut -d: -f1)
if [ -z "$STORY_LINE" ]; then
    echo "❌ Error: Story $STORY_ID not found in sprint-status.yaml"
    exit 1
fi

# Update status to done
sed -i "${STORY_LINE}s/in-progress/done/" docs/sprint-artifacts/sprint-status.yaml
sed -i "${STORY_LINE}s/ready-for-dev/done/" docs/sprint-artifacts/sprint-status.yaml
sed -i "${STORY_LINE}s/review/done/" docs/sprint-artifacts/sprint-status.yaml

# Add completion date if not present
if ! grep -q "COMPLETED $(date +%Y-%m-%d)" docs/sprint-artifacts/sprint-status.yaml; then
    sed -i "${STORY_LINE}s/$/ - COMPLETED $(date +%Y-%m-%d)/" docs/sprint-artifacts/sprint-status.yaml
fi

echo "✅ Sprint status updated"

# 2. Run tests
echo "🧪 Running tests..."
if ! venv/bin/pytest tests/ -v --tb=short; then
    echo "❌ Tests failed! Fix tests before completing story."
    exit 1
fi
echo "✅ All tests passing"

# 3. Commit
echo "💾 Committing changes..."
git add .
STORY_TITLE=$(grep "$STORY_ID" docs/sprint-artifacts/sprint-status.yaml | head -1 | sed 's/.*: //' | cut -d'#' -f1 | xargs)
git commit -m "Implement Story $STORY_ID: $STORY_TITLE

- All acceptance criteria met
- All tests passing
- Sprint status updated to done

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

echo "✅ Changes committed"

# 4. Merge to main
echo "🔀 Merging to main..."
git checkout main
git pull origin main
git merge "$BRANCH_NAME" --no-edit

echo "✅ Merged to main"

# 5. Push
echo "📤 Pushing to remote..."
git push origin main

echo "✅ Pushed to remote"

# 6. Summary
echo ""
echo "🎉 Story $STORY_ID completed successfully!"
echo "   ✅ Status updated"
echo "   ✅ Tests passing"
echo "   ✅ Committed"
echo "   ✅ Merged to main"
echo "   ✅ Pushed to remote"
echo ""
echo "Ready for next story! Run: execute dev${DEV_NUM}_tier5.md"
