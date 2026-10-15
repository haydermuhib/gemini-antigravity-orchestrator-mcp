---
name: gemini-orchestrator
description: >-
  Use this skill when Google Gemini or external LLMs orchestrate Antigravity IDE, browse global and workspace skills, or run coordinated agent workflows.
---

# Gemini Antigravity Orchestrator Skill

This skill explains how external Gemini models connect to and orchestrate Google Antigravity IDE via the MCP server.

## Key Capabilities
1. **Catalog Browsing**: Discover over 160+ curated Antigravity skills across design, architecture, debugging, and verification.
2. **Plugin Inspection**: Inspect installed plugins like `cursor-team-kit`, `pstack`, and `ponytail`.
3. **Task Orchestration**: Execute workspace commands, track progress through transcripts, and inspect generated artifacts.

## Usage Runbook
1. Use `get_antigravity_status` to view active workspace directories and configuration roots.
2. Use `search_skills` to find specialized design or workflow guidelines.
3. Read the selected skill using `get_skill`.
4. Perform atomic actions via `execute_workspace_command`.
5. Verify output artifacts using `list_artifacts` and `read_artifact`.
