#!/bin/bash
# overview.sh - Comprehensive project progress overview
# Shows total backlog, tier progress, and wave status

SPRINT_STATUS="docs/sprint-artifacts/sprint-status.yaml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RGrid - Project Progress Overview"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================================================
# TOTAL BACKLOG (All Epics)
# ============================================================================

echo "🎯 TOTAL BACKLOG - All Epics"
echo "────────────────────────────────────────────────────────────────────"

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
echo "────────────────────────────────────────────────────────────────────"

for TIER in 1 2 3 4 5 6; do
    case $TIER in
        1) TIER_NAME="Foundation" ;;
        2) TIER_NAME="Demo-Ready" ;;
        3) TIER_NAME="Production-Ready" ;;
        4) TIER_NAME="Distributed Cloud" ;;
        5) TIER_NAME="Advanced Features" ;;
        6) TIER_NAME="Production Polish" ;;
    esac

    # Count Tier stories (approximate based on typical story patterns)
    case $TIER in
        1) PATTERN="1-[1-6]-" ;;
        2) PATTERN="(2-[1-2]|8-[1-2]|NEW-[12])-" ;;
        3) PATTERN="(2-3|NEW-[3567])-" ;;
        4) PATTERN="(3-[1-4]|4-[1-5]|NEW-4)-" ;;
        5) PATTERN="(2-[45]|5-[3-6]|6-[1-4]|7-[2356])-" ;;
        6) PATTERN="(8-[3-6]|9-[1-5]|10-)-" ;;
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
# TIER 4 DETAILED (Distributed Cloud)
# ============================================================================

echo "🚀 TIER 4 - Distributed Execution & Cloud (DETAILED)"
echo "────────────────────────────────────────────────────────────────────"

# Tier 4 stories from epics 3 and 4 + NEW stories
T4_STORIES=(
    "2-5:Handle Input Files"
    "3-1:Ray Head Node"
    "3-2:Ray Workers"
    "3-3:Ray Task Distribution"
    "3-4:Worker Health Monitoring"
    "4-1:Hetzner Provisioning"
    "4-2:Queue-based Provisioning"
    "4-3:Billing Hour Termination"
    "4-4:Pre-pull Docker Images"
    "4-5:Worker Auto-Replacement"
    "NEW-4:Provisioning Feedback"
    "NEW-7:Dead Worker Detection"
)

T4_DONE=0
T4_TOTAL=${#T4_STORIES[@]}

echo "  Epic 3 - Ray Cluster:"
for story in "3-1" "3-2" "3-3" "3-4"; do
    STATUS=$(grep "^  $story-" $SPRINT_STATUS | grep -o ": [a-z-]*" | cut -d: -f2 | xargs)
    TITLE=$(echo "${T4_STORIES[@]}" | grep -o "$story:[^:]*" | cut -d: -f2)

    if [ "$STATUS" = "done" ]; then
        echo -e "    ${GREEN}✅${NC} $story - $TITLE"
        T4_DONE=$((T4_DONE + 1))
    elif [ "$STATUS" = "in-progress" ]; then
        echo -e "    ${BLUE}🔵${NC} $story - $TITLE"
    else
        echo -e "    📋 $story - $TITLE"
    fi
done

echo ""
echo "  Epic 4 - Hetzner Cloud:"
for story in "4-1" "4-2" "4-3" "4-4" "4-5"; do
    STATUS=$(grep "^  $story-" $SPRINT_STATUS | grep -o ": [a-z-]*" | cut -d: -f2 | xargs)
    TITLE=$(echo "${T4_STORIES[@]}" | grep -o "$story:[^:]*" | cut -d: -f2)

    if [ "$STATUS" = "done" ]; then
        echo -e "    ${GREEN}✅${NC} $story - $TITLE"
        T4_DONE=$((T4_DONE + 1))
    elif [ "$STATUS" = "in-progress" ]; then
        echo -e "    ${BLUE}🔵${NC} $story - $TITLE"
    else
        echo -e "    📋 $story - $TITLE"
    fi
done

echo ""
echo "  Additional Stories:"
for story in "2-5" "NEW-4" "NEW-7"; do
    STATUS=$(grep "^  $story-" $SPRINT_STATUS | grep -o ": [a-z-]*" | cut -d: -f2 | xargs)
    TITLE=$(echo "${T4_STORIES[@]}" | grep -o "$story:[^:]*" | cut -d: -f2)

    if [ "$STATUS" = "done" ]; then
        echo -e "    ${GREEN}✅${NC} $story - $TITLE"
        T4_DONE=$((T4_DONE + 1))
    elif [ "$STATUS" = "in-progress" ]; then
        echo -e "    ${BLUE}🔵${NC} $story - $TITLE"
    else
        echo -e "    📋 $story - $TITLE"
    fi
done

T4_PERCENT=$((T4_DONE * 100 / T4_TOTAL))
echo ""
printf "  Total: %d/%d stories (%d%%) " $T4_DONE $T4_TOTAL $T4_PERCENT
if [ $T4_PERCENT -eq 100 ]; then
    echo -e "${GREEN}✅ COMPLETE${NC}"
else
    echo -e "${BLUE}🔵 IN PROGRESS${NC}"
fi
echo ""

# ============================================================================
# TIER 5 DETAILED (Advanced Features) + WAVE BREAKDOWN
# ============================================================================

echo "⚡ TIER 5 - Advanced Features & Optimization (DETAILED)"
echo "────────────────────────────────────────────────────────────────────"

# Tier 5 stories organized by phase
declare -A T5_STORIES
T5_STORIES["Phase 1: MinIO Storage"]="7-2:Output Collection,7-3:Retention Policy"
T5_STORIES["Phase 2: File Management"]="7-1:Upload Inputs,7-4:Download Outputs,7-5:Remote-only Flag"
T5_STORIES["Phase 3: Batch"]="5-3:Progress Tracking,5-4:Output Organization,5-5:Failure Handling,5-6:Batch Retry"
T5_STORIES["Phase 4: Dependencies"]="2-4:Auto-detect Deps"
T5_STORIES["Phase 5: Caching"]="6-1:Script Hashing,6-2:Dependency Caching,6-3:Cache Invalidation,6-4:Input Caching"
T5_STORIES["Phase 6: Optimization"]="7-6:Large File Streaming"

T5_DONE=0
T5_TOTAL=0

for phase in "Phase 1: MinIO Storage" "Phase 2: File Management" "Phase 3: Batch" "Phase 4: Dependencies" "Phase 5: Caching" "Phase 6: Optimization"; do
    echo "  $phase:"
    IFS=',' read -ra STORIES <<< "${T5_STORIES[$phase]}"
    for story_info in "${STORIES[@]}"; do
        story_id=$(echo $story_info | cut -d: -f1)
        story_title=$(echo $story_info | cut -d: -f2)

        STATUS=$(grep "^  $story_id-" $SPRINT_STATUS | grep -o ": [a-z-]*" | cut -d: -f2 | xargs)

        T5_TOTAL=$((T5_TOTAL + 1))

        if [ "$STATUS" = "done" ]; then
            echo -e "    ${GREEN}✅${NC} $story_id - $story_title"
            T5_DONE=$((T5_DONE + 1))
        elif [ "$STATUS" = "in-progress" ]; then
            echo -e "    ${BLUE}🔵${NC} $story_id - $story_title ${YELLOW}(IN PROGRESS)${NC}"
        elif [ "$STATUS" = "review" ]; then
            echo -e "    ${YELLOW}👀${NC} $story_id - $story_title ${YELLOW}(REVIEW)${NC}"
        else
            echo -e "    📋 $story_id - $story_title"
        fi
    done
    echo ""
done

T5_PERCENT=$((T5_DONE * 100 / T5_TOTAL))
printf "  Total: %d/%d stories (%d%%) " $T5_DONE $T5_TOTAL $T5_PERCENT
if [ $T5_PERCENT -eq 100 ]; then
    echo -e "${GREEN}✅ COMPLETE${NC}"
elif [ $T5_PERCENT -gt 0 ]; then
    echo -e "${BLUE}🔵 IN PROGRESS${NC}"
else
    echo -e "📋 TODO"
fi
echo ""

# ============================================================================
# TIER 5 WAVE BREAKDOWN
# ============================================================================

echo "🌊 TIER 5 - Wave Progress"
echo "────────────────────────────────────────────────────────────────────"

# Wave 1
WAVE1_STORIES=("7-2" "7-3" "2-4" "6-1")
WAVE1_DONE=0
echo "  Wave 1 (Foundation):"
for story in "${WAVE1_STORIES[@]}"; do
    STATUS=$(grep "^  $story-" $SPRINT_STATUS | grep -o ": [a-z-]*" | cut -d: -f2 | xargs)
    if [ "$STATUS" = "done" ]; then
        WAVE1_DONE=$((WAVE1_DONE + 1))
        echo -e "    ${GREEN}✅${NC} $story"
    else
        echo -e "    📋 $story"
    fi
done
echo -e "    Status: $WAVE1_DONE/4 complete"
echo ""

# Wave 2
WAVE2_STORIES=("2-5" "5-3" "6-2")
WAVE2_DONE=0
WAVE2_PROGRESS=0
echo "  Wave 2 (Current):"
for story in "${WAVE2_STORIES[@]}"; do
    STATUS=$(grep "^  $story-" $SPRINT_STATUS | grep -o ": [a-z-]*" | cut -d: -f2 | xargs)
    if [ "$STATUS" = "done" ]; then
        WAVE2_DONE=$((WAVE2_DONE + 1))
        echo -e "    ${GREEN}✅${NC} $story"
    elif [ "$STATUS" = "in-progress" ]; then
        WAVE2_PROGRESS=$((WAVE2_PROGRESS + 1))
        echo -e "    ${BLUE}🔵${NC} $story ${YELLOW}(IN PROGRESS)${NC}"
    elif [ "$STATUS" = "review" ]; then
        echo -e "    ${YELLOW}👀${NC} $story ${YELLOW}(REVIEW)${NC}"
    else
        echo -e "    📋 $story"
    fi
done
echo -e "    Status: $WAVE2_DONE/3 done, $WAVE2_PROGRESS in progress"
echo ""

# Wave 3
WAVE3_STORIES=("7-5" "5-4" "6-3")
echo "  Wave 3 (Next):"
for story in "${WAVE3_STORIES[@]}"; do
    echo -e "    📋 $story"
done
echo -e "    Status: Ready when Wave 2 completes"
echo ""

# Remaining
echo "  Remaining Waves:"
echo "    📋 Wave 4: 5-5, 7-1 (+ others)"
echo "    📋 Wave 5: 5-6, 7-6, 6-4"
echo ""

# ============================================================================
# SUMMARY & NEXT STEPS
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 SUMMARY & NEXT STEPS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Current focus
CURRENT_STORIES=$(grep -E "^  [0-9]+-[0-9]+-" $SPRINT_STATUS | grep "in-progress" | wc -l)
if [ $CURRENT_STORIES -gt 0 ]; then
    echo "🎯 Current Focus:"
    grep -E "^  [0-9]+-[0-9]+-" $SPRINT_STATUS | grep "in-progress" | sed 's/^  /  /' | head -5
    echo ""
fi

# What's next
echo "⏭️  What's Next:"
if [ $WAVE2_DONE -eq 3 ]; then
    echo "  ✅ Wave 2 complete - Ready to start Wave 3!"
    echo "  📝 Action: Run 'execute devX_tier5.md' in each session"
elif [ $WAVE2_PROGRESS -gt 0 ]; then
    echo "  ⏳ Wave 2 in progress ($WAVE2_DONE/3 done)"
    echo "  📝 Action: Wait for devs to finish, then use ./complete-story.sh"
else
    echo "  📋 Check sprint-status.yaml for current state"
fi
echo ""

# Recent activity
echo "📅 Recent Activity:"
git log --oneline --since="1 day ago" | head -5 | sed 's/^/  /'
if [ $(git log --oneline --since="1 day ago" | wc -l) -eq 0 ]; then
    echo "  (No commits in last 24 hours)"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Quick Commands:"
echo "  ./overview.sh       - This overview (run anytime)"
echo "  ./status.sh         - Quick status check"
echo "  ./complete-story.sh - Finish a story"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
