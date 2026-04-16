# MCP Server Guidance — Deep Implement

Use these tools when available to improve implementation quality. Skip any section whose tools are not in your current context.

---

## Context7

**When:** Before writing code for each section, especially when using unfamiliar APIs.

- Use `resolve-library-id` then `query-docs` to look up API signatures, configuration options, and usage patterns
- Check docs before writing integration code — prevents hallucinated method names and wrong parameter orders
- Particularly valuable for test setup (framework-specific assertions, mocking patterns)

## Serena

**When:** Throughout implementation — code navigation, understanding, and editing.

**Navigation (prefer over grep+read):**
- `find_symbol` with `include_body=False` to discover classes/functions, then `include_body=True` for the ones you need
- `find_referencing_symbols` to find all usages before modifying a symbol
- `get_symbols_overview` to understand file structure without reading entire files
- `search_for_pattern` for text-based searches (error messages, config values, comments)

**Editing (use for precise symbol-level changes):**
- `replace_symbol_body` to rewrite a function/method/class
- `insert_after_symbol` / `insert_before_symbol` to add new code at the right location
- `rename_symbol` for refactoring names across the codebase

**Key principle:** If you're looking for code symbols (functions, classes, variables), use Serena. If you're looking for text patterns (error messages, config values), use grep.

## Playwright

**When:** After implementing UI-facing sections, for functional verification.

- Use `browser_navigate` to load the application
- Use `browser_snapshot` to get the accessibility tree (faster than screenshots for structure verification)
- Use `browser_take_screenshot` for visual verification of layout and styling
- Use `browser_click`, `browser_fill_form`, `browser_type` to test user interactions
- Use `browser_console_messages` and `browser_network_requests` to check for errors
- Useful for verifying that implemented UI matches section requirements

## Chrome DevTools

**When:** Debugging failures, performance analysis, or inspecting runtime behavior.

- `list_console_messages` / `get_console_message` — check for JavaScript errors after page load
- `list_network_requests` / `get_network_request` — verify API calls are correct (URLs, payloads, status codes)
- `take_screenshot` — capture current page state for visual debugging
- `performance_start_trace` / `performance_stop_trace` / `performance_analyze_insight` — profile slow pages
- `lighthouse_audit` — run automated accessibility, performance, and best practices checks
- Use when tests fail or behavior is unexpected — DevTools gives you the "why"

---

## User Customization

If `~/.claude/deep-trilogy/mcp-guidance.md` exists, read it now for additional MCP server guidance configured by the user.
