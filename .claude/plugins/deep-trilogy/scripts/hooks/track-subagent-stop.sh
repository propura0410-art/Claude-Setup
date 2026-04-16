#!/bin/bash
# Remove completed subagent from tracking file.
# Receives JSON on stdin with agent_id field.

input=$(cat)
AGENT_ID=$(echo "$input" | jq -r '.agent_id // empty')

[ -z "$AGENT_ID" ] && exit 0

SESSION_ID=$(echo "$input" | jq -r '.session_id // "default"')
AGENT_FILE="/tmp/claude-subagents-${SESSION_ID}.json"

[ ! -f "$AGENT_FILE" ] && exit 0

UPDATED=$(jq --arg id "$AGENT_ID" '.agents |= map(select(.id != $id))' "$AGENT_FILE" 2>/dev/null)
if [ -n "$UPDATED" ]; then
    echo "$UPDATED" > "$AGENT_FILE"
fi

# Clean up empty files
COUNT=$(jq '.agents | length' "$AGENT_FILE" 2>/dev/null || echo "0")
[ "$COUNT" = "0" ] && rm -f "$AGENT_FILE"
exit 0
