# MCP Server Guidance — Deep Plan

Use these tools when available to improve research and planning quality. Skip any section whose tools are not in your current context.

---

## Context7

**When:** Research phase (steps 6-7), before writing specs or plans.

- Use `resolve-library-id` to find the correct Context7 identifier for libraries/frameworks mentioned in the spec
- Use `query-docs` to pull current API references, configuration options, and best practices
- Prefer Context7 over web search for known libraries — the docs are pre-indexed and more reliable
- Include relevant API details in `claude-research.md` so downstream planning is grounded in real APIs

## Serena

**When:** Research phase, when understanding existing codebase structure.

- Use `get_symbols_overview` to understand file structure before reading entire files
- Use `find_symbol` with `include_body=False` first to discover relevant classes/functions, then `include_body=True` only for the ones you need
- Use `find_referencing_symbols` to understand how existing code is used before planning changes
- Use `search_for_pattern` for text-based searches (error messages, config values) that aren't symbol names
- Prefer Serena over grep+read for all code navigation — it's token-efficient and semantically aware

---

## User Customization

If `~/.claude/deep-trilogy/mcp-guidance.md` exists, read it now for additional MCP server guidance configured by the user.
