---
name: deep-setup
description: One-time setup for the deep-trilogy plugin. Configures the statusline, context tracking, and subagent hooks. Run this after installing the plugin.
---

# Deep Trilogy Setup

This skill configures the deep-trilogy statusline and hooks for your Claude Code environment.

## What It Does

1. Installs a 3-line statusline (context bar, session info, git + deep-trilogy status)
2. Enables context percentage tracking for deep-trilogy checkpoints
3. Configures subagent tracking hooks

## Steps

### 0. Resolve Plugin Root

Look for `DEEP_PLUGIN_ROOT=<path>` in your conversation context. Extract the path value.

If not found:
```bash
find ~/.claude/plugins/cache -name "plugin.json" -path "*avi8or*deep-trilogy*" -type f 2>/dev/null | head -1 | xargs dirname | xargs dirname
```

### 1. Check Dependencies

```bash
which jq && which git
```

If `jq` is missing, tell user: `brew install jq`

### 2. Confirm With User

Explain what will change:
- **statusLine**: Will be set to the deep-trilogy statusline script
- **If they have an existing statusline**: Warn it will be replaced. The new one includes everything the old one did (context tracking) plus git status, cost, and deep-trilogy integration.

Ask the user to confirm.

### 3. Update Settings

The statusline command points to the plugin cache path:

```json
{
  "statusLine": {
    "type": "command",
    "command": "<plugin_root>/scripts/tools/statusline.sh",
    "padding": 0
  }
}
```

Use the Read tool to read `~/.claude/settings.json`, update the `statusLine` field with the resolved plugin_root path, and write it back with the Edit tool.

### 4. Verify

Tell the user:

```
Setup complete! Deep-trilogy statusline is now configured.

To activate: restart Claude Code (exit and relaunch).

You'll see:
  Line 1: Context window progress bar (full width)
  Line 2: Model, project, git status, cache %, duration, cost
  Line 3: Git branch + deep-trilogy phase (when active)

Requires: Nerd Font in your terminal for icons.
```
