"""
MCP Prompts Registry for Antigravity.
Exposes prompt workflows to help Google Gemini orchestrate Antigravity tasks.
"""

from typing import Dict, List, Any


def get_prompt_definitions() -> List[Dict[str, Any]]:
    return [
        {
            "name": "orchestrate-task",
            "description": "Guides Google Gemini in selecting relevant Antigravity skills, inspecting workspace rules, and issuing coordinated actions.",
            "arguments": [
                {
                    "name": "goal",
                    "description": "The specific objective or task to achieve in the workspace.",
                    "required": True
                },
                {
                    "name": "design_aesthetic",
                    "description": "Optional UI/UX aesthetic (e.g., bento, editorial, minimal, retro, glassmorphism).",
                    "required": False
                }
            ]
        },
        {
            "name": "audit-customizations",
            "description": "Prompts Gemini to perform a thorough audit of the project's skills, rules, and plugins.",
            "arguments": []
        }
    ]


def get_prompt_content(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "orchestrate-task":
        goal = arguments.get("goal", "")
        aesthetic = arguments.get("design_aesthetic", "bento")
        return {
            "description": f"Orchestrating task: {goal}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"""You are orchestrating Google Antigravity IDE to execute the following goal:
Goal: {goal}
Preferred Aesthetic: {aesthetic}

Please follow these orchestration steps using your Antigravity MCP tools:
1. Call `list_rules` to discover workspace-specific policies (GEMINI.md / AGENTS.md).
2. Call `search_skills` with query keywords related to '{goal}' and '{aesthetic}'.
3. Fetch the full procedure using `get_skill` for the chosen skill.
4. Execute required steps using `execute_workspace_command`.
5. Check generated outputs or artifacts via `list_artifacts` and `read_artifact`.
6. Summarize the accomplished work clearly.
"""
                    }
                }
            ]
        }
        
    elif name == "audit-customizations":
        return {
            "description": "Audit Antigravity customizations",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": """Inspect all available Antigravity skills, plugins, and rules:
1. Call `get_antigravity_status` to view system health and paths.
2. Call `list_plugins` to see installed plugin bundles.
3. Call `list_skills` with scope='workspace' to review project-specific skills.
4. Call `list_rules` to verify coding standards and constraints.
Present an executive summary of the workspace customizations.
"""
                    }
                }
            ]
        }
        
    raise ValueError(f"Unknown prompt: {name}")
