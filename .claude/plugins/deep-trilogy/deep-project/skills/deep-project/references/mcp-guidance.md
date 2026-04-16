# MCP Server Guidance — Deep Project

Use these tools when available to improve project decomposition quality. Skip any section whose tools are not in your current context.

---

## Context7

**When:** During tech stack research and requirements analysis.

- Use `resolve-library-id` then `query-docs` to understand frameworks/libraries mentioned in the requirements
- Helps inform split boundaries — knowing a library's module structure can suggest natural decomposition points
- Check docs for integration patterns between libraries to identify coupling that affects split design

## Serena

**When:** During codebase exploration to inform split decisions.

- Use `get_symbols_overview` on key directories to understand module boundaries
- Use `find_symbol` to check if functionality already exists before creating a split for it
- Use `find_referencing_symbols` to understand coupling between modules — high coupling suggests they belong in the same split
- Use `list_dir` to explore project structure before proposing split directories
- Prefer Serena over grep+read — it gives semantic understanding, not just text matches

---

## User Customization

If `~/.claude/deep-trilogy/mcp-guidance.md` exists, read it now for additional MCP server guidance configured by the user.
