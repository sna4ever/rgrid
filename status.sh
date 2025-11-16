#!/bin/bash
# status.sh - Comprehensive status across all tiers and full backlog

SPRINT_STATUS="docs/sprint-artifacts/sprint-status.yaml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RGrid Development Status - $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================================================
# TOTAL BACKLOG
# ============================================================================

echo "🎯 TOTAL BACKLOG"
echo "────────────────────────────────────────────────────────"

TOTAL_STORIES=$(grep -E "^  [0-9]+-[0-9]+-" $SPRINT_STATUS | wc -l)
DONE_STORIES=$(grep -E "^  [0-9]+-[0-9]+-" $SPRINT_STATUS | grep ": done" | wc -l)
IN_PROGRESS=$(grep -E "^  [0-9]+-[0-9]+-" $SPRINT_STATUS | grep ": in-progress" | wc -l)
REVIEW=$(grep -E "^  [0-9]+-[0-9]+-" $SPRINT_STATUS | grep ": review" | wc -l)
READY=$(grep -E "^  [0-9]+-[0-9]+-" $SPRINT_STATUS | grep ": ready-for-dev" | wc -l)

TOTAL_PERCENT=$((DONE_STORIES * 100 / TOTAL_STORIES))

echo -e "  Total Stories: ${BLUE}$TOTAL_STORIES${NC}"
echo -e "  ✅ Done: ${GREEN}$DONE_STORIES${NC} ($TOTAL_PERCENT%)"
echo -e "  🔵 In Progress: ${BLUE}$IN_PROGRESS${NC}"
echo -e "  👀 In Review: ${YELLOW}$REVIEW${NC}"
echo -e "  📋 Ready: $READY"
echo ""

# Progress bar
BAR_WIDTH=50
FILLED=$((TOTAL_PERCENT * BAR_WIDTH / 100))
EMPTY=$((BAR_WIDTH - FILLED))
printf "  ["
printf "%${FILLED}s" | tr ' ' '█'
printf "%${EMPTY}s" | tr ' ' '░'
printf "] %d%%\n" $TOTAL_PERCENT
echo ""

# ============================================================================
# TIER BREAKDOWN
# ============================================================================

echo "📚 TIER BREAKDOWN"
echo "────────────────────────────────────────────────────────"

for TIER in 1 2 3 4 5 6; do
    case $TIER in
        1) TIER_NAME="Foundation" ;;
        2) TIER_NAME="Demo-Ready" ;;
        3) TIER_NAME="Production-Ready" ;;
        4) TIER_NAME="Distributed Cloud" ;;
        5) TIER_NAME="Advanced Features" ;;
        6) TIER_NAME="Production Polish" ;;
    esac

    # Count Tier stories
    case $TIER in
        1) PATTERN="1-[1-6]-" ;;
        2) PATTERN="(2-[1-2]|8-[1-2]|NEW-[12])-" ;;
        3) PATTERN="(2-3|2-4|10-4|7-6|NEW-[3567])-" ;;
        4) PATTERN="(3-[1-4]|4-[1-5]|NEW-4)-" ;;
        5) PATTERN="(2-5|5-[3-6]|6-[1-4]|7-[235])-" ;;
        6) PATTERN="(8-[3-6]|9-[1-5]|10-[1-3568])-" ;;
    esac

    TIER_TOTAL=$(grep -E "^  $PATTERN" $SPRINT_STATUS 2>/dev/null | wc -l)
    TIER_DONE=$(grep -E "^  $PATTERN" $SPRINT_STATUS 2>/dev/null | grep ": done" | wc -l)

    if [ $TIER_TOTAL -gt 0 ]; then
        TIER_PERCENT=$((TIER_DONE * 100 / TIER_TOTAL))

        if [ $TIER_PERCENT -eq 100 ]; then
            STATUS="${GREEN}✅ COMPLETE${NC}"
        elif [ $TIER_PERCENT -gt 0 ]; then
            STATUS="${BLUE}🔵 IN PROGRESS${NC}"
        else
            STATUS="📋 TODO"
        fi

        printf "  Tier %d - %-20s %2d/%2d stories (%3d%%) %b\n" \
            $TIER "$TIER_NAME" $TIER_DONE $TIER_TOTAL $TIER_PERCENT "$STATUS"
    fi
done

echo ""

# ============================================================================
# CURRENT ACTIVITY
# ============================================================================

echo "⚡ CURRENT ACTIVITY"
echo "────────────────────────────────────────────────────────"

# Show in-progress stories
if [ $IN_PROGRESS -gt 0 ]; then
    echo -e "  ${BLUE}🔵 In Progress ($IN_PROGRESS):${NC}"
    grep -E "^  [0-9]+-[0-9]+-" $SPRINT_STATUS | grep "in-progress" | sed 's/: in-progress//' | sed 's/^  /     /'
    echo ""
fi

# Show review stories
if [ $REVIEW -gt 0 ]; then
    echo -e "  ${YELLOW}👀 In Review ($REVIEW):${NC}"
    grep -E "^  [0-9]+-[0-9]+-" $SPRINT_STATUS | grep "review" | sed 's/: review//' | sed 's/^  /     /'
    echo ""
fi

# Show completed today
TODAY=$(date +%Y-%m-%d)
COMPLETED_TODAY=$(grep "COMPLETED $TODAY" $SPRINT_STATUS | wc -l)
if [ $COMPLETED_TODAY -gt 0 ]; then
    echo -e "  ${GREEN}✅ Completed Today ($COMPLETED_TODAY):${NC}"
    grep "COMPLETED $TODAY" $SPRINT_STATUS | sed 's/^  /     /'
    echo ""
fi

# If nothing active
if [ $IN_PROGRESS -eq 0 ] && [ $REVIEW -eq 0 ] && [ $COMPLETED_TODAY -eq 0 ]; then
    echo "  No active work at the moment"
    echo ""
fi

# ============================================================================
# NEXT UP
# ============================================================================

echo "📋 NEXT AVAILABLE STORIES"
echo "────────────────────────────────────────────────────────"

NEXT_STORIES=$(grep -E "^  [0-9]+-[0-9]+-" $SPRINT_STATUS | grep "ready-for-dev" | head -5)
if [ -n "$NEXT_STORIES" ]; then
    echo "$NEXT_STORIES" | sed 's/: ready-for-dev.*//' | sed 's/^  /  /'
else
    echo "  No stories ready for development"
fi
echo ""

# ============================================================================
# GIT STATUS
# ============================================================================

echo "🌿 GIT STATUS"
echo "────────────────────────────────────────────────────────"

# Active branches
BRANCHES=$(git branch | grep "story-" | wc -l)
if [ $BRANCHES -gt 0 ]; then
    echo "  Active Story Branches ($BRANCHES):"
    git branch | grep "story-" | sed 's/^/    /'
else
    echo "  No active story branches"
fi
echo ""

# Recent commits
echo "  Recent Commits (last 3):"
git log --oneline -3 | sed 's/^/    /'
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Quick Commands:"
echo "  ./status.sh         - This quick status (run anytime)"
echo "  ./overview.sh       - Detailed tier/wave breakdown"
echo "  ./complete-story.sh - Complete and merge a story"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
