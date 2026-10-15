"""
Tools Registry and Schemas for Antigravity MCP Server.
Compliant with Model Context Protocol (MCP) tool specification.
"""

from typing import Dict, List, Any
from .antigravity_engine import AntigravityEngine


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Returns the JSON schemas for all available MCP tools."""
    return [
        {
            "name": "get_antigravity_status",
            "description": "Returns the real-time status of Google Antigravity IDE, including active workspace paths, config locations, total skills/plugins/rules counts, and system environment.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        },
        {
            "name": "list_known_workspaces",
            "description": "Discovers and lists all known development projects and workspaces on the user's system, showing which one is currently active.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        },
        {
            "name": "set_active_workspace",
            "description": "Dynamically switches the active workspace to another folder/repository on the user's machine at runtime. All subsequent commands, skills, and rules will target this new workspace without restarting the server.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "workspace_path": {
                        "type": "string",
                        "description": "Path to the target workspace folder (e.g. '/home/haider/Desktop/MyGithub/projectB')."
                    }
                },
                "required": ["workspace_path"],
                "additionalProperties": False
            }
        },
        {
            "name": "list_skills",
            "description": "Discovers and lists all skills available to Antigravity agents. Can filter by scope ('all', 'workspace', 'global', 'builtin', 'plugins') or by plugin name.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["all", "workspace", "global", "builtin", "plugins"],
                        "default": "all",
                        "description": "Scope of skills to retrieve."
                    },
                    "plugin_filter": {
                        "type": "string",
                        "description": "Optional plugin name (e.g. 'cursor-team-kit', 'ponytail', 'pstack') to only return skills provided by that plugin."
                    }
                },
                "additionalProperties": False
            }
        },
        {
            "name": "get_skill",
            "description": "Retrieves the complete instructions (SKILL.md), YAML frontmatter, procedures, and associated scripts/references/examples for a specific Antigravity skill.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name or directory identifier of the skill (e.g. 'bento', 'subagent-driven-development', 'deslop', 'systematic-debugging')."
                    }
                },
                "required": ["skill_name"],
                "additionalProperties": False
            }
        },
        {
            "name": "search_skills",
            "description": "Searches skills by natural language query or keywords across skill names and descriptions to find the right procedure for a task.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or intent (e.g. 'modern web design', 'debugging', 'code review', 'git worktree', 'planning')."
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        },
        {
            "name": "list_plugins",
            "description": "Lists all installed Antigravity plugins across workspace and global configurations (~/.gemini/config/plugins), including their manifests, descriptions, versions, exposed skills, and subagents.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        },
        {
            "name": "get_plugin_details",
            "description": "Gets full configuration, manifest metadata, rules, and MCP definitions of a specific plugin (e.g. 'cursor-team-kit', 'ponytail', 'pstack').",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plugin_name": {
                        "type": "string",
                        "description": "The folder name of the plugin."
                    }
                },
                "required": ["plugin_name"],
                "additionalProperties": False
            }
        },
        {
            "name": "list_rules",
            "description": "Discovers all active rules across workspace (GEMINI.md, AGENTS.md, .agents/rules/*.md) and global settings (~/.gemini/config/rules/*.md).",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        },
        {
            "name": "get_rule",
            "description": "Reads the full content and triggers of an Antigravity rule file by name or path.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_identifier": {
                        "type": "string",
                        "description": "Name or file path of the rule (e.g. 'GEMINI.md', 'AGENTS.md', or custom rule name)."
                    }
                },
                "required": ["rule_identifier"],
                "additionalProperties": False
            }
        },
        {
            "name": "list_conversations",
            "description": "Lists recent Antigravity IDE conversations, timestamps, artifacts counts, and status from the brain store.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        },
        {
            "name": "get_conversation_transcript",
            "description": "Inspects the execution transcript of an Antigravity conversation, allowing Gemini to review recent agent steps, user prompts, thoughts, and tool invocations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "Optional conversation UUID. Defaults to the most recent/active conversation."
                    },
                    "limit": {
                        "type": "integer",
                        "default": 15,
                        "description": "Maximum number of recent events to retrieve."
                    }
                },
                "additionalProperties": False
            }
        },
        {
            "name": "list_artifacts",
            "description": "Lists generated artifacts (plans, code diffs, reports, diagrams) in the Antigravity conversation brain directory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "Optional conversation UUID. Defaults to the most recent conversation."
                    }
                },
                "additionalProperties": False
            }
        },
        {
            "name": "read_artifact",
            "description": "Reads the markdown or code content of a specific artifact file.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "artifact_name_or_path": {
                        "type": "string",
                        "description": "Filename or path of the artifact (e.g. 'analysis_results.md')."
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "Optional conversation UUID."
                    }
                },
                "required": ["artifact_name_or_path"],
                "additionalProperties": False
            }
        },
        {
            "name": "execute_workspace_command",
            "description": "Executes a shell command directly in the Antigravity workspace, capturing stdout, stderr, exit code, and execution time.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run (e.g. 'git status', 'ls -la', 'npm test')."
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional working directory. Defaults to the workspace root."
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 30,
                        "description": "Timeout in seconds."
                    }
                },
                "required": ["command"],
                "additionalProperties": False
            }
        },
        {
            "name": "create_workspace_skill",
            "description": "Scaffolds a new Antigravity skill adhering to the Antigravity Customization System (creates SKILL.md with YAML frontmatter).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name in lowercase hyphenated format (e.g. 'deploy-preview', 'fastapi-scaffold')."
                    },
                    "description": {
                        "type": "string",
                        "description": "When the agent should use this skill. Written in third-person."
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Markdown instructions, procedures, and runbook steps for the skill."
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["workspace", "global"],
                        "default": "workspace",
                        "description": "Target scope. 'workspace' puts it in .agents/skills/<name>, 'global' in ~/.gemini/config/skills/<name>."
                    }
                },
                "required": ["name", "description", "instructions"],
                "additionalProperties": False
            }
        },
        {
            "name": "create_workspace_rule",
            "description": "Creates an Antigravity rule in the workspace (.agents/rules/*.md or GEMINI.md) or global settings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Rule filename (e.g. 'code-style.md' or 'GEMINI.md')."
                    },
                    "content": {
                        "type": "string",
                        "description": "Rule instructions in markdown."
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["workspace", "global"],
                        "default": "workspace",
                        "description": "'workspace' or 'global'."
                    },
                    "trigger": {
                        "type": "string",
                        "enum": ["always_on", "model_decision"],
                        "default": "always_on",
                        "description": "When the rule should be loaded into context."
                    }
                },
                "required": ["filename", "content"],
                "additionalProperties": False
            }
        },
        {
            "name": "orchestrate_agent_workflow",
            "description": "Formulates an end-to-end execution blueprint for a task by identifying required Antigravity skills, applicable rules, and steps.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The user's objective or feature request."
                    },
                    "preferred_aesthetic": {
                        "type": "string",
                        "description": "Optional UI/design aesthetic if building frontend (e.g. 'bento', 'neobrutalism', 'glassmorphism', 'minimal')."
                    }
                },
                "required": ["task"],
                "additionalProperties": False
            }
        }
    ]


def handle_tool_call(engine: AntigravityEngine, name: str, args: Dict[str, Any]) -> Any:
    """Dispatches a tool call to the engine implementation."""
    if name == "get_antigravity_status":
        return engine.get_ide_status()
        
    elif name == "list_known_workspaces":
        return engine.list_known_workspaces()
        
    elif name == "set_active_workspace":
        ws_path = args.get("workspace_path")
        return engine.set_active_workspace(ws_path)

    elif name == "list_skills":
        scope = args.get("scope", "all")
        plugin_filter = args.get("plugin_filter")
        return engine.list_skills(scope=scope, plugin_filter=plugin_filter)
        
    elif name == "get_skill":
        skill_name = args.get("skill_name")
        res = engine.get_skill_details(skill_name)
        return res if res else {"error": f"Skill '{skill_name}' not found."}
        
    elif name == "search_skills":
        query = args.get("query", "")
        return engine.search_skills(query)
        
    elif name == "list_plugins":
        return engine.list_plugins()
        
    elif name == "get_plugin_details":
        pname = args.get("plugin_name")
        res = engine.get_plugin_details(pname)
        return res if res else {"error": f"Plugin '{pname}' not found."}
        
    elif name == "list_rules":
        return engine.list_rules()
        
    elif name == "get_rule":
        r_id = args.get("rule_identifier")
        res = engine.get_rule_content(r_id)
        return res if res else {"error": f"Rule '{r_id}' not found."}
        
    elif name == "list_conversations":
        return engine.list_conversations()
        
    elif name == "get_conversation_transcript":
        cid = args.get("conversation_id")
        limit = args.get("limit", 15)
        return engine.get_conversation_transcript(conversation_id=cid, limit=limit)
        
    elif name == "list_artifacts":
        cid = args.get("conversation_id")
        return engine.list_artifacts(conversation_id=cid)
        
    elif name == "read_artifact":
        aname = args.get("artifact_name_or_path")
        cid = args.get("conversation_id")
        content = engine.read_artifact(aname, conversation_id=cid)
        return {"artifact": aname, "content": content} if content else {"error": f"Artifact '{aname}' not found."}
        
    elif name == "execute_workspace_command":
        cmd = args.get("command")
        cwd = args.get("cwd")
        timeout = args.get("timeout", 30)
        return engine.execute_command(cmd, cwd=cwd, timeout=timeout)
        
    elif name == "create_workspace_skill":
        s_name = args.get("name")
        desc = args.get("description")
        inst = args.get("instructions")
        scope = args.get("scope", "workspace")
        return engine.create_skill(name=s_name, description=desc, instructions=inst, scope=scope)
        
    elif name == "create_workspace_rule":
        fname = args.get("filename")
        content = args.get("content")
        scope = args.get("scope", "workspace")
        trigger = args.get("trigger", "always_on")
        return engine.create_rule(filename=fname, content=content, scope=scope, trigger=trigger)
        
    elif name == "orchestrate_agent_workflow":
        task = args.get("task", "")
        preferred_aesthetic = args.get("preferred_aesthetic")
        
        # Discover matching skills
        matching_skills = engine.search_skills(task)[:5]
        aesthetic_skill = None
        if preferred_aesthetic:
            aesthetic_matches = engine.search_skills(preferred_aesthetic)
            if aesthetic_matches:
                aesthetic_skill = aesthetic_matches[0]

        active_rules = [r["name"] for r in engine.list_rules()]
        
        return {
            "task": task,
            "recommended_skills": [s["name"] for s in matching_skills],
            "design_system_skill": aesthetic_skill["name"] if aesthetic_skill else "bento",
            "active_rules_in_effect": active_rules,
            "orchestration_workflow": [
                {"phase": "1. Discovery & Planning", "action": f"Consult skill '{matching_skills[0]['name']}'" if matching_skills else "Review workspace requirements", "tool": "get_skill"},
                {"phase": "2. Visual Foundation", "action": f"Apply design patterns from skill '{aesthetic_skill['name'] if aesthetic_skill else 'bento'}'", "tool": "get_skill"},
                {"phase": "3. Implementation", "action": "Execute development steps, create components and pages", "tool": "execute_workspace_command"},
                {"phase": "4. Verification", "action": "Verify behavior and inspect generated artifacts", "tool": "list_artifacts"}
            ]
        }

    else:
        raise ValueError(f"Unknown tool: {name}")
