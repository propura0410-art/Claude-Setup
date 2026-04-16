#!/bin/bash
# Track active subagents by appending to a session-scoped temp file.
# Receives JSON on stdin with agent_id, agent_type fields.

input=$(cat)
AGENT_ID=$(echo "$input" | jq -r '.agent_id // empty')
AGENT_TYPE=$(echo "$input" | jq -r '.agent_type // "unknown"')

[ -z "$AGENT_ID" ] && exit 0

# Session-scoped file to avoid cross-session pollution
SESSION_ID=$(echo "$input" | jq -r '.session_id // "default"')
AGENT_FILE="/tmp/claude-subagents-${SESSION_ID}.json"

# Create or update the file atomically
if [ -f "$AGENT_FILE" ]; then
    UPDATED=$(jq --arg id "$AGENT_ID" --arg type "$AGENT_TYPE" --arg start "$(date +%s)" \
        '.agents += [{"id": $id, "type": $type, "start": ($start | tonumber)}]' \
        "$AGENT_FILE" 2>/dev/null)
    [ -n "$UPDATED" ] && echo "$UPDATED" > "$AGENT_FILE"
else
    jq -n --arg id "$AGENT_ID" --arg type "$AGENT_TYPE" --arg start "$(date +%s)" \
        '{"agents": [{"id": $id, "type": $type, "start": ($start | tonumber)}]}' \
        > "$AGENT_FILE"
fi
