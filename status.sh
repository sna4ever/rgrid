#!/bin/bash
# status.sh - Show current Tier 5 wave status

echo "📊 Tier 5 Development Status - $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Count statuses
TOTAL_T5=$(grep -E "^  (2-4|2-5|5-3|5-4|5-5|5-6|6-1|6-2|6-3|6-4|7-2|7-3|7-4|7-5|7-6)" docs/sprint-artifacts/sprint-status.yaml | wc -l)
DONE=$(grep -E "^  (2-4|2-5|5-3|5-4|5-5|5-6|6-1|6-2|6-3|6-4|7-2|7-3|7-4|7-5|7-6)" docs/sprint-artifacts/sprint-status.yaml | grep "done" | wc -l)
IN_PROGRESS=$(grep -E "^  (2-4|2-5|5-3|5-4|5-5|5-6|6-1|6-2|6-3|6-4|7-2|7-3|7-4|7-5|7-6)" docs/sprint-artifacts/sprint-status.yaml | grep "in-progress" | wc -l)
REVIEW=$(grep -E "^  (2-4|2-5|5-3|5-4|5-5|5-6|6-1|6-2|6-3|6-4|7-2|7-3|7-4|7-5|7-6)" docs/sprint-artifacts/sprint-status.yaml | grep "review" | wc -l)

PERCENT=$((DONE * 100 / TOTAL_T5))

echo "📈 Overall Progress: $DONE/$TOTAL_T5 stories ($PERCENT%)"
echo ""

# Show in-progress stories
if [ $IN_PROGRESS -gt 0 ]; then
    echo "🔵 In Progress ($IN_PROGRESS):"
    grep -E "^  (2-4|2-5|5-3|5-4|5-5|5-6|6-1|6-2|6-3|6-4|7-2|7-3|7-5|7-6)" docs/sprint-artifacts/sprint-status.yaml | grep "in-progress" | sed 's/^  /  /'
    echo ""
fi

# Show review stories
if [ $REVIEW -gt 0 ]; then
    echo "👀 In Review ($REVIEW):"
    grep -E "^  (2-4|2-5|5-3|5-4|5-5|5-6|6-1|6-2|6-3|6-4|7-2|7-3|7-5|7-6)" docs/sprint-artifacts/sprint-status.yaml | grep "review" | sed 's/^  /  /'
    echo ""
fi

# Show completed today
TODAY=$(date +%Y-%m-%d)
COMPLETED_TODAY=$(grep "COMPLETED $TODAY" docs/sprint-artifacts/sprint-status.yaml | wc -l)
if [ $COMPLETED_TODAY -gt 0 ]; then
    echo "✅ Completed Today ($COMPLETED_TODAY):"
    grep "COMPLETED $TODAY" docs/sprint-artifacts/sprint-status.yaml | sed 's/^  /  /'
    echo ""
fi

# Show active branches
BRANCHES=$(git branch | grep "story-" | wc -l)
if [ $BRANCHES -gt 0 ]; then
    echo "🌿 Active Story Branches ($BRANCHES):"
    git branch | grep "story-" | sed 's/^/  /'
    echo ""
fi

# Show recent commits
echo "💾 Recent Commits (last 5):"
git log --oneline -5 | sed 's/^/  /'
echo ""

# Show next available stories
echo "📋 Next Available Stories:"
grep -E "^  (2-4|2-5|5-3|5-4|5-5|5-6|6-1|6-2|6-3|6-4|7-5|7-6)" docs/sprint-artifacts/sprint-status.yaml | grep "ready-for-dev" | head -3 | sed 's/^  /  /'
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Run './status.sh' anytime to refresh | './complete-story.sh' to finish a story"
