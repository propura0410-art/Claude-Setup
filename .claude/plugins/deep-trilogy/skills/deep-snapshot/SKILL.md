---
name: deep-snapshot
description: Sync snapshot to current session for safe /clear. Run when statusline shows stale snapshot indicator.
---

# Deep Snapshot

Syncs the nearest snapshot.json to your current session so `/deep-resume` works after `/clear`.

## Steps

### 1. Resolve Plugin Root

Look for `DEEP_PLUGIN_ROOT=<path>` in your conversation context. Extract the path value.

If not found:
```bash
find ~/.claude/plugins/cache -name "plugin.json" -path "*avi8or*deep-trilogy*" -type f 2>/dev/null | head -1 | xargs dirname | xargs dirname
```

### 2. Resolve Session ID

Look for `DEEP_SESSION_ID=<value>` in your conversation context. Extract the value.

### 3. Run Sync

```bash
python3 <plugin_root>/scripts/tools/update-snapshot-session.py --session-id "<session_id>"
```

### 4. Report Result

- If `"status": "synced"` → Tell user: "Snapshot synced. Safe to /clear."
- If `"status": "already_synced"` → Tell user: "Snapshot already current. Safe to /clear."
- If `"status": "not_found"` → Tell user: "No active deep-trilogy session found."
- If `"status": "error"` → Show the error message.
