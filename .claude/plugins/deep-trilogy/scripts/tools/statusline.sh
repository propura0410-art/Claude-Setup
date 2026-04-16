#!/bin/bash
# Deep Trilogy Statusline — ships with deep-trilogy 2.0.0
#
# 3-line Claude Code statusline:
#   Line 1: Full-width context window progress bar
#   Line 2: Model, project, git status, cache %, duration, cost
#   Line 3: Git branch + deep-trilogy phase/progress/subagents/snapshot
#
# Receives JSON on stdin from Claude Code. Outputs ANSI-colored text.
# Lines with no content are not printed (graceful degradation).
#
# Dependencies: jq, Nerd Font in terminal, git (optional)

set -euo pipefail

# ── Read input ────────────────────────────────────────────────────
input=$(cat)

# ── Parse JSON fields ─────────────────────────────────────────────
MODEL_ID=$(echo "$input" | jq -r '.model.id // ""')
MODEL_DISPLAY=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
CWD=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
PROJECT_DIR=$(echo "$input" | jq -r '.workspace.project_dir // ""')
SESSION_ID=$(echo "$input" | jq -r '.session_id // ""')

PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
[ -z "$PCT" ] && PCT=0

COST=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
DURATION_MS=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')

CACHE_READ=$(echo "$input" | jq -r '.context_window.current_usage.cache_read_input_tokens // 0')
CACHE_CREATE=$(echo "$input" | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0')

WORKTREE_NAME=$(echo "$input" | jq -r '.worktree.name // ""')

CONTEXT_SIZE=$(echo "$input" | jq -r '.context_window.context_window_size // 200000')
[ "$CONTEXT_SIZE" -le 0 ] && CONTEXT_SIZE=200000

# Write context pct to shared file (for deep-trilogy PreCompact hook)
echo "$PCT" > /tmp/claude-context-pct 2>/dev/null

# ── Context segment measurement ─────────────────────────────────
# Gray = project files (CLAUDE.md, MEMORY.md) + system prompt estimate
# Purple = plugin overhead (everything else loaded before conversation)
# Conversation = growth since session baseline
TOTAL_USED=$((CONTEXT_SIZE * PCT / 100))
BASELINE_FILE="/tmp/statusline-baseline-${SESSION_ID:-default}"

if [ ! -f "$BASELINE_FILE" ]; then
    # First render: measure gray tokens from known files
    GRAY_CHARS=0
    [ -f "$HOME/.claude/CLAUDE.md" ] && GRAY_CHARS=$((GRAY_CHARS + $(wc -c < "$HOME/.claude/CLAUDE.md" | tr -d ' ')))
    if [ -n "$PROJECT_DIR" ]; then
        CLAUDE_PATH=$(echo "$PROJECT_DIR" | tr '/' '-')
        P_CLAUDE="$HOME/.claude/projects/${CLAUDE_PATH}/CLAUDE.md"
        P_MEMORY="$HOME/.claude/projects/${CLAUDE_PATH}/memory/MEMORY.md"
        [ -f "$P_CLAUDE" ] && GRAY_CHARS=$((GRAY_CHARS + $(wc -c < "$P_CLAUDE" | tr -d ' ')))
        [ -f "$P_MEMORY" ] && GRAY_CHARS=$((GRAY_CHARS + $(wc -c < "$P_MEMORY" | tr -d ' ')))
    fi
    GRAY_TOKENS=$(( (GRAY_CHARS / 4) + 3000 ))
    [ "$GRAY_TOKENS" -gt "$TOTAL_USED" ] && GRAY_TOKENS=$TOTAL_USED
    PURPLE_TOKENS=$((TOTAL_USED - GRAY_TOKENS))
    BASELINE_TOTAL=$TOTAL_USED
    CONV_TOKENS=0
    echo "${GRAY_TOKENS}|${PURPLE_TOKENS}|${BASELINE_TOTAL}" > "$BASELINE_FILE" 2>/dev/null
else
    BASELINE_DATA=$(cat "$BASELINE_FILE")
    GRAY_TOKENS=$(echo "$BASELINE_DATA" | cut -d'|' -f1)
    PURPLE_TOKENS=$(echo "$BASELINE_DATA" | cut -d'|' -f2)
    BASELINE_TOTAL=$(echo "$BASELINE_DATA" | cut -d'|' -f3)
    CONV_TOKENS=$((TOTAL_USED - BASELINE_TOTAL))
    [ "$CONV_TOKENS" -lt 0 ] && CONV_TOKENS=0
fi

FREE_TOKENS=$((CONTEXT_SIZE - TOTAL_USED))
[ "$FREE_TOKENS" -lt 0 ] && FREE_TOKENS=0

# ── Terminal width ────────────────────────────────────────────────
COLS=$(tput cols 2>/dev/null || echo 80)

# ── Colors ────────────────────────────────────────────────────────
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
CYAN='\033[36m'
PURPLE='\033[35m'
BLUE='\033[34m'
WHITE='\033[37m'
BOLD_GREEN='\033[1;32m'
BOLD_YELLOW='\033[1;33m'
BOLD_RED='\033[1;31m'
BOLD_CYAN='\033[1;36m'
BOLD_PURPLE='\033[1;35m'
BOLD_WHITE='\033[1;37m'
DIM_WHITE='\033[2;37m'

# Background colors for progress bar
BG_GREEN='\033[42m'
BG_YELLOW='\033[43m'
BG_RED='\033[41m'
BG_DARK='\033[100m'
BG_GRAY='\033[48;5;240m'
BG_PURPLE='\033[48;5;133m'

# ── Model display ────────────────────────────────────────────────
# claude-opus-4-6 → Opus 4.6, claude-sonnet-4-6 → Sonnet 4.6
model_label() {
    local id="$1"
    local display="$2"
    case "$id" in
        claude-opus-4-6*)    echo "Opus 4.6" ;;
        claude-sonnet-4-6*)  echo "Sonnet 4.6" ;;
        claude-haiku-4-5*)   echo "Haiku 4.5" ;;
        *)                   echo "$display" ;;
    esac
}
MODEL=$(model_label "$MODEL_ID" "$MODEL_DISPLAY")

# ── Format duration ──────────────────────────────────────────────
format_duration() {
    local ms="$1"
    local total_sec=$((ms / 1000))
    local hours=$((total_sec / 3600))
    local mins=$(( (total_sec % 3600) / 60 ))
    local secs=$((total_sec % 60))
    if [ "$hours" -gt 0 ]; then
        echo "${hours}h${mins}m"
    elif [ "$mins" -gt 0 ]; then
        echo "${mins}m"
    else
        echo "${secs}s"
    fi
}
DURATION=$(format_duration "$DURATION_MS")

# ── Format cost ──────────────────────────────────────────────────
COST_FMT=$(printf '$%.2f' "$COST")

# ── Cache hit ratio ──────────────────────────────────────────────
CACHE_PCT=""
if [ "$CACHE_READ" != "0" ] || [ "$CACHE_CREATE" != "0" ]; then
    CACHE_TOTAL=$((CACHE_READ + CACHE_CREATE))
    if [ "$CACHE_TOTAL" -gt 0 ]; then
        CACHE_PCT=$((CACHE_READ * 100 / CACHE_TOTAL))
    fi
fi

# ── Git info (cached 5s) ─────────────────────────────────────────
GIT_CACHE="/tmp/statusline-git-cache-${SESSION_ID:-default}"
GIT_BRANCH=""
GIT_DIRTY_COUNT=""

refresh_git() {
    local git_dir="${CWD:-.}"
    if git -C "$git_dir" rev-parse --git-dir > /dev/null 2>&1; then
        local branch
        branch=$(git -C "$git_dir" branch --show-current 2>/dev/null || echo "")
        local dirty
        dirty=$(git -C "$git_dir" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
        echo "${branch}|${dirty}" > "$GIT_CACHE"
    else
        echo "|" > "$GIT_CACHE"
    fi
}

if [ -f "$GIT_CACHE" ]; then
    CACHE_AGE=$(( $(date +%s) - $(stat -f %m "$GIT_CACHE" 2>/dev/null || stat -c %Y "$GIT_CACHE" 2>/dev/null || echo 0) ))
    [ "$CACHE_AGE" -gt 5 ] && refresh_git
else
    refresh_git
fi

if [ -f "$GIT_CACHE" ]; then
    GIT_DATA=$(cat "$GIT_CACHE")
    GIT_BRANCH="${GIT_DATA%%|*}"
    GIT_DIRTY_COUNT="${GIT_DATA##*|}"
fi

# ── Project directory name ───────────────────────────────────────
DIR_NAME=""
if [ -n "$PROJECT_DIR" ]; then
    DIR_NAME="${PROJECT_DIR##*/}"
elif [ -n "$CWD" ]; then
    DIR_NAME="${CWD##*/}"
fi
# Fallback for home-relative paths
[ -z "$DIR_NAME" ] && DIR_NAME="~"

# ── Deep-trilogy detection (cached 5s) ───────────────────────────
DT_CACHE="/tmp/statusline-dt-cache-${SESSION_ID:-default}"
DT_PLUGIN=""
DT_PROGRESS=""
DT_SNAPSHOT_STATUS=""

refresh_dt() {
    local search_dir="${CWD:-.}"
    local snap_path=""

    # Search upward for snapshot.json
    local dir="$search_dir"
    for _ in 1 2 3 4; do
        if [ -f "$dir/snapshot.json" ]; then
            snap_path="$dir/snapshot.json"
            break
        elif [ -f "$dir/implementation/snapshot.json" ]; then
            snap_path="$dir/implementation/snapshot.json"
            break
        fi
        local parent
        parent=$(dirname "$dir")
        [ "$parent" = "$dir" ] && break
        dir="$parent"
    done

    if [ -z "$snap_path" ]; then
        echo "||" > "$DT_CACHE"
        return
    fi

    # Parse snapshot
    local plugin snap_session_id
    plugin=$(jq -r '.plugin // ""' "$snap_path" 2>/dev/null)
    snap_session_id=$(jq -r '.session_id // ""' "$snap_path" 2>/dev/null)

    # Progress
    local section_completed section_total progress=""
    section_completed=$(jq -r '.section_progress.completed // 0' "$snap_path" 2>/dev/null)
    section_total=$(jq -r '.section_progress.total // 0' "$snap_path" 2>/dev/null)
    if [ "$section_total" != "0" ] && [ "$section_total" != "null" ]; then
        progress="s${section_completed}/${section_total}"
    fi

    # Snapshot sync status
    local sync_status="stale"
    if [ -n "$SESSION_ID" ] && [ "$snap_session_id" = "$SESSION_ID" ]; then
        sync_status="ready"
    fi

    echo "${plugin}|${progress}|${sync_status}" > "$DT_CACHE"
}

if [ -f "$DT_CACHE" ]; then
    DT_AGE=$(( $(date +%s) - $(stat -f %m "$DT_CACHE" 2>/dev/null || stat -c %Y "$DT_CACHE" 2>/dev/null || echo 0) ))
    [ "$DT_AGE" -gt 5 ] && refresh_dt
else
    refresh_dt
fi

if [ -f "$DT_CACHE" ]; then
    DT_DATA=$(cat "$DT_CACHE")
    DT_PLUGIN=$(echo "$DT_DATA" | cut -d'|' -f1)
    DT_PROGRESS=$(echo "$DT_DATA" | cut -d'|' -f2)
    DT_SNAPSHOT_STATUS=$(echo "$DT_DATA" | cut -d'|' -f3)
fi

# ── Subagent count ───────────────────────────────────────────────
SUB_COUNT=0
SUB_FILE="/tmp/claude-subagents-${SESSION_ID:-default}.json"
if [ -f "$SUB_FILE" ]; then
    SUB_COUNT=$(jq '.agents | length' "$SUB_FILE" 2>/dev/null || echo 0)
fi

# ═══════════════════════════════════════════════════════════════════
# LINE 1: Multi-segment context bar (iPhone storage style)
#   Gray = system prompt + CLAUDE.md    Purple = plugins
#   Green/Yellow/Red = conversation     Dark = free space
# ═══════════════════════════════════════════════════════════════════

# Conversation segment color based on total percentage
if [ "$PCT" -ge 80 ]; then
    CONV_BG="$BG_RED"
elif [ "$PCT" -ge 60 ]; then
    CONV_BG="$BG_YELLOW"
else
    CONV_BG="$BG_GREEN"
fi

# Bar dimensions
BAR_WIDTH=$((COLS - 2))
[ "$BAR_WIDTH" -lt 10 ] && BAR_WIDTH=10

# Distribute used width among gray/purple/conv proportionally
USED_W=$((PCT * BAR_WIDTH / 100))

if [ "$TOTAL_USED" -gt 0 ]; then
    GRAY_W=$((GRAY_TOKENS * USED_W / TOTAL_USED))
    PURPLE_W=$((PURPLE_TOKENS * USED_W / TOTAL_USED))
else
    GRAY_W=0; PURPLE_W=0
fi

# Minimum 1 char for non-zero segments
[ "$GRAY_TOKENS" -gt 0 ] && [ "$GRAY_W" -lt 1 ] && GRAY_W=1
[ "$PURPLE_TOKENS" -gt 0 ] && [ "$PURPLE_W" -lt 1 ] && PURPLE_W=1

# Conversation gets remainder of used space
CONV_W=$((USED_W - GRAY_W - PURPLE_W))
[ "$CONV_W" -lt 0 ] && CONV_W=0

# Free gets the rest
FREE_W=$((BAR_WIDTH - GRAY_W - PURPLE_W - CONV_W))
[ "$FREE_W" -lt 0 ] && FREE_W=0

# Center percentage text in the bar
PCT_TEXT="${PCT}%"
PCT_LEN=${#PCT_TEXT}
CENTER=$((  (BAR_WIDTH - PCT_LEN) / 2 ))
PCT_END=$((CENTER + PCT_LEN))

# Render a bar segment with optional percentage text overlay
# Usage: render_segment <start_pos> <width> <bg_color>
render_segment() {
    local pos=$1 width=$2 bg=$3
    [ "$width" -le 0 ] && return
    local end=$((pos + width))
    local ol_s=$((CENTER > pos ? CENTER : pos))
    local ol_e=$((PCT_END < end ? PCT_END : end))
    if [ "$ol_s" -ge "$ol_e" ]; then
        # No overlap with percentage text — just spaces
        printf '%b%*s%b' "$bg" "$width" "" "$RESET"
    else
        # Percentage text overlaps this segment
        local pre=$((ol_s - pos))
        local post=$((end - ol_e))
        local ts=$((ol_s - CENTER))
        local tl=$((ol_e - ol_s))
        printf '%b' "$bg"
        [ "$pre" -gt 0 ] && printf '%*s' "$pre" ""
        printf '%b%s' "$BOLD_WHITE" "${PCT_TEXT:$ts:$tl}"
        [ "$post" -gt 0 ] && printf '%*s' "$post" ""
        printf '%b' "$RESET"
    fi
}

# Build the bar
printf '▐'
render_segment 0 "$GRAY_W" "$BG_GRAY"
render_segment "$GRAY_W" "$PURPLE_W" "$BG_PURPLE"
render_segment "$((GRAY_W + PURPLE_W))" "$CONV_W" "$CONV_BG"
render_segment "$((GRAY_W + PURPLE_W + CONV_W))" "$FREE_W" "$BG_DARK"
printf '▌\n'

# ═══════════════════════════════════════════════════════════════════
# LINE 2: Session info
# ═══════════════════════════════════════════════════════════════════

line2=""

# Model
line2="${BOLD_WHITE}${MODEL}${RESET}"

# Project dir with repo icon
line2="${line2}  ${BOLD_CYAN}󰳏 ${DIR_NAME}${RESET}"

# Git tree status (clean/dirty)
if [ -n "$GIT_BRANCH" ]; then
    if [ -z "$GIT_DIRTY_COUNT" ] || [ "$GIT_DIRTY_COUNT" = "0" ]; then
        # Clean tree: nf-md-source_branch_check (green)
        line2="${line2}  ${BOLD_GREEN}󱓏${RESET}"
    else
        # Dirty tree: nf-md-source_branch_sync + delta count (yellow)
        line2="${line2}  ${BOLD_YELLOW}󱓎 Δ${GIT_DIRTY_COUNT}${RESET}"
    fi
fi

# Cache hit ratio
if [ -n "$CACHE_PCT" ]; then
    line2="${line2}  ${WHITE}⚡${CACHE_PCT}%${RESET}"
fi

# Duration
line2="${line2}  ${DIM_WHITE} ${DURATION}${RESET}"

# Cost
line2="${line2}  ${DIM_WHITE}${COST_FMT}${RESET}"

printf '%b\n' "$line2"

# ═══════════════════════════════════════════════════════════════════
# LINE 3: Git branch + Deep Trilogy (conditional)
# ═══════════════════════════════════════════════════════════════════

line3=""

# Git branch
if [ -n "$GIT_BRANCH" ]; then
    if [ -n "$WORKTREE_NAME" ]; then
        line3="${BOLD_PURPLE} wt:${WORKTREE_NAME}${RESET}"
    else
        line3="${BOLD_PURPLE} ${GIT_BRANCH}${RESET}"
    fi
fi

# Deep-trilogy phase
if [ -n "$DT_PLUGIN" ]; then
    case "$DT_PLUGIN" in
        deep-project) line3="${line3}  ✨ project" ;;
        deep-plan)    line3="${line3}  🧠 plan" ;;
        deep-implement) line3="${line3}  🛠️ impl" ;;
    esac

    # Progress
    if [ -n "$DT_PROGRESS" ]; then
        line3="${line3} ${DT_PROGRESS}"
    fi
fi

# Subagent count
if [ "$SUB_COUNT" -gt 0 ]; then
    line3="${line3}  ${WHITE}⚙${SUB_COUNT} sub${RESET}"
fi

# Snapshot status
if [ -n "$DT_PLUGIN" ] && [ -n "$DT_SNAPSHOT_STATUS" ]; then
    if [ "$DT_SNAPSHOT_STATUS" = "ready" ]; then
        line3="${line3}  ${BOLD_GREEN}󰄁 snapshot${RESET}"
    else
        line3="${line3}  ${BLUE}󱗙 snapshot${RESET}"
    fi
fi

# Only print line 3 if it has content
if [ -n "$line3" ]; then
    printf '%b\n' "$line3"
fi
