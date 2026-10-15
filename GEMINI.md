# Workspace Rules for Google Antigravity & Gemini Orchestration

These rules apply automatically to Google Antigravity IDE and connected Gemini orchestrators.

## Core Directives
1. **Model Context Protocol (MCP)**: Use the `antigravity-orchestrator` MCP server to discover project skills, query guidelines, and coordinate subtasks.
2. **Progressive Disclosure**: When tackling tasks, search and inspect skills via `search_skills` and `get_skill` instead of hallucinating procedures.
3. **Verification First**: Verify changes using `execute_workspace_command` before declaring work done.
