"""
Antigravity Engine - Discovery, parsing, inspection, and execution core
for Google Antigravity IDE and Workspace/Global Customizations.
"""

import os
import re
import sys
import json
import glob
import time
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class AntigravityEngine:
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.home_dir = Path.home()
        self.gemini_dir = self.home_dir / ".gemini"
        self.global_config_dir = self.gemini_dir / "config"
        self.antigravity_ide_dir = self.gemini_dir / "antigravity-ide"
        self.brain_dir = self.antigravity_ide_dir / "brain"
        self.builtin_skills_dir = self.antigravity_ide_dir / "builtin" / "skills"
        
        # Workspace customizations root
        self.workspace_agents_dir = self.workspace_root / ".agents"

    def set_active_workspace(self, workspace_path: str) -> Dict[str, Any]:
        """Switches the active workspace dynamically at runtime without restarting the server."""
        target = Path(workspace_path).expanduser().resolve()
        if not target.is_dir():
            raise ValueError(f"Directory does not exist: {workspace_path}")
            
        self.workspace_root = target
        self.workspace_agents_dir = target / ".agents"
        
        rules = self.list_rules()
        ws_skills = self.list_skills(scope="workspace")
        
        return {
            "success": True,
            "message": f"Active workspace switched to: {target}",
            "workspace_root": str(target),
            "workspace_rules_count": len(rules),
            "workspace_skills_count": len(ws_skills),
            "has_agents_dir": self.workspace_agents_dir.is_dir(),
            "has_git": (target / ".git").is_dir()
        }

    def list_known_workspaces(self) -> List[Dict[str, Any]]:
        """Discovers and lists known development workspaces across user projects and Antigravity."""
        workspaces: List[Dict[str, Any]] = []
        seen = set()

        def add_ws(p: Path):
            p_resolved = p.resolve()
            p_str = str(p_resolved)
            if p_str not in seen and p_resolved.is_dir():
                seen.add(p_str)
                workspaces.append({
                    "name": p_resolved.name,
                    "path": p_str,
                    "is_active": p_resolved == self.workspace_root,
                    "has_git": (p_resolved / ".git").is_dir(),
                    "has_agents": (p_resolved / ".agents").is_dir() or (p_resolved / "GEMINI.md").is_file()
                })

        # 1. Current workspace
        add_ws(self.workspace_root)

        # 2. Check ~/Desktop/MyGithub/*
        my_github = self.home_dir / "Desktop" / "MyGithub"
        if my_github.is_dir():
            for item in my_github.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    add_ws(item)

        # 3. Check common development project paths
        for candidate_root in [self.home_dir / "Projects", self.home_dir / "src", self.home_dir / "Desktop"]:
            if candidate_root.is_dir():
                for item in candidate_root.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        if (item / ".git").is_dir() or (item / ".agents").is_dir() or (item / "package.json").is_file() or (item / "pixi.toml").is_file():
                            add_ws(item)

        return sorted(workspaces, key=lambda w: (not w["is_active"], w["name"]))
        
    def get_ide_status(self) -> Dict[str, Any]:
        """Returns the real-time status and paths of the Antigravity IDE environment."""
        recent_convs = self.list_conversations()
        active_conv = recent_convs[0] if recent_convs else None
        
        skills = self.list_skills(scope="all")
        plugins = self.list_plugins()
        rules = self.list_rules()
        
        return {
            "workspace_root": str(self.workspace_root),
            "antigravity_ide_dir": str(self.antigravity_ide_dir),
            "global_config_dir": str(self.global_config_dir),
            "brain_dir": str(self.brain_dir),
            "active_conversation": active_conv,
            "counts": {
                "total_skills": len(skills),
                "total_plugins": len(plugins),
                "total_rules": len(rules),
                "recent_conversations": len(recent_convs)
            },
            "environment": {
                "python_version": sys.version.split()[0],
                "node_version": subprocess.getoutput("node --version") if shutil.which("node") else "not installed",
                "platform": platform.system()
            }
        }

    # -------------------------------------------------------------------------
    # SKILLS DISCOVERY & INSPECTION
    # -------------------------------------------------------------------------

    def _parse_skill_file(self, skill_md_path: Path, scope: str, plugin_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not skill_md_path.is_file():
            return None
        
        try:
            content = skill_md_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return None
            
        skill_dir = skill_md_path.parent
        name = skill_dir.name
        description = ""
        metadata = {}
        
        # Parse YAML frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_text = parts[1]
                # Simple YAML extractor without external deps
                for line in yaml_text.splitlines():
                    line_strip = line.strip()
                    if line_strip.startswith("name:"):
                        name = line_strip.split("name:", 1)[1].strip().strip('"\'')
                    elif line_strip.startswith("description:"):
                        description = line_strip.split("description:", 1)[1].strip().strip('"\'')
                # If multiline description (YAML >- or |)
                if not description or description in (">-", ">", "|"):
                    desc_match = re.search(r"description:\s*[>|\-]*\n((?:\s{2,}.*\n?)+)", yaml_text)
                    if desc_match:
                        description = " ".join([l.strip() for l in desc_match.group(1).splitlines() if l.strip()])
                metadata["raw_frontmatter"] = yaml_text.strip()
        
        if not description:
            # Fallback to first heading / paragraph
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("---"):
                    description = line
                    break

        has_scripts = (skill_dir / "scripts").is_dir()
        has_references = (skill_dir / "references").is_dir()
        has_examples = (skill_dir / "examples").is_dir()
        has_resources = (skill_dir / "resources").is_dir()

        return {
            "name": name,
            "directory_name": skill_dir.name,
            "description": description.strip(),
            "scope": scope,
            "plugin": plugin_name,
            "path": str(skill_dir),
            "skill_file": str(skill_md_path),
            "components": {
                "scripts": has_scripts,
                "references": has_references,
                "examples": has_examples,
                "resources": has_resources,
            }
        }

    def list_skills(self, scope: str = "all", plugin_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists skills discovered across global, workspace, builtin, and plugin scopes."""
        skills: List[Dict[str, Any]] = []
        seen_names = set()

        def add_skill(skill_dict: Optional[Dict[str, Any]]):
            if skill_dict and skill_dict["name"] not in seen_names:
                seen_names.add(skill_dict["name"])
                skills.append(skill_dict)

        # 1. Workspace Skills (.agents/skills/*)
        if scope in ("all", "workspace"):
            ws_skills_dir = self.workspace_agents_dir / "skills"
            if ws_skills_dir.is_dir():
                for item in ws_skills_dir.iterdir():
                    if item.is_dir() and (item / "SKILL.md").is_file():
                        add_skill(self._parse_skill_file(item / "SKILL.md", scope="workspace"))

        # 2. Plugins Skills (~/.gemini/config/plugins/<plugin>/skills/* and .agents/plugins/<plugin>/skills/*)
        if scope in ("all", "plugin", "plugins"):
            plugin_roots = [self.global_config_dir / "plugins"]
            if self.workspace_agents_dir.is_dir():
                plugin_roots.append(self.workspace_agents_dir / "plugins")

            for proot in plugin_roots:
                if proot.is_dir():
                    for pdir in proot.iterdir():
                        if pdir.is_dir():
                            pname = pdir.name
                            if plugin_filter and plugin_filter != pname:
                                continue
                            pskills = pdir / "skills"
                            if pskills.is_dir():
                                for sdir in pskills.iterdir():
                                    if sdir.is_dir() and (sdir / "SKILL.md").is_file():
                                        add_skill(self._parse_skill_file(sdir / "SKILL.md", scope="plugin", plugin_name=pname))

        # 3. Global Skills (~/.gemini/config/skills/*)
        if scope in ("all", "global"):
            global_skills_dir = self.global_config_dir / "skills"
            if global_skills_dir.is_dir():
                for item in global_skills_dir.iterdir():
                    if item.is_dir() and (item / "SKILL.md").is_file():
                        add_skill(self._parse_skill_file(item / "SKILL.md", scope="global"))

        # 4. Built-in Skills (~/.gemini/antigravity-ide/builtin/skills/*)
        if scope in ("all", "builtin"):
            if self.builtin_skills_dir.is_dir():
                for item in self.builtin_skills_dir.iterdir():
                    if item.is_dir() and (item / "SKILL.md").is_file():
                        add_skill(self._parse_skill_file(item / "SKILL.md", scope="builtin"))

        return sorted(skills, key=lambda s: s["name"])

    def get_skill_details(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves complete skill documentation, instructions, scripts, and references."""
        all_skills = self.list_skills(scope="all")
        matched = None
        for s in all_skills:
            if s["name"] == skill_name or s["directory_name"] == skill_name:
                matched = s
                break
                
        if not matched:
            return None

        skill_dir = Path(matched["path"])
        skill_file = Path(matched["skill_file"])
        
        full_markdown = skill_file.read_text(encoding="utf-8", errors="replace")

        # Discover scripts, references, resources, examples
        def list_subfiles(subname: str) -> List[Dict[str, str]]:
            subdir = skill_dir / subname
            files = []
            if subdir.is_dir():
                for p in subdir.glob("**/*"):
                    if p.is_file():
                        files.append({
                            "name": p.name,
                            "relative_path": str(p.relative_to(skill_dir)),
                            "absolute_path": str(p)
                        })
            return files

        return {
            **matched,
            "full_content": full_markdown,
            "files": {
                "scripts": list_subfiles("scripts"),
                "references": list_subfiles("references"),
                "examples": list_subfiles("examples"),
                "resources": list_subfiles("resources")
            }
        }

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """Searches skills by name, description, and keywords with relevance ranking."""
        skills = self.list_skills(scope="all")
        query_words = [w.lower() for w in re.split(r"[\s\-_]+", query) if w]
        scored_skills = []

        for skill in skills:
            score = 0
            name_lower = skill["name"].lower()
            desc_lower = skill["description"].lower()

            for w in query_words:
                if w in name_lower:
                    score += 10
                if w in desc_lower:
                    score += 3
                    
            if score > 0:
                scored_skills.append({**skill, "match_score": score})

        return sorted(scored_skills, key=lambda s: s["match_score"], reverse=True)

    # -------------------------------------------------------------------------
    # PLUGINS DISCOVERY & INSPECTION
    # -------------------------------------------------------------------------

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Lists all installed plugins and their manifests."""
        plugins = []
        plugin_dirs = [self.global_config_dir / "plugins"]
        if self.workspace_agents_dir.is_dir():
            plugin_dirs.append(self.workspace_agents_dir / "plugins")

        seen = set()
        for p_root in plugin_dirs:
            if not p_root.is_dir():
                continue
            for item in p_root.iterdir():
                if item.is_dir() and item.name not in seen:
                    manifest_file = item / "plugin.json"
                    manifest = {}
                    if manifest_file.is_file():
                        try:
                            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                        except Exception:
                            manifest = {}
                    
                    skills_dir = item / "skills"
                    exposed_skills = []
                    if skills_dir.is_dir():
                        exposed_skills = [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()]

                    agents_dir = item / "agents"
                    exposed_agents = []
                    if agents_dir.is_dir():
                        exposed_agents = [d.stem for d in agents_dir.iterdir()]

                    plugins.append({
                        "name": item.name,
                        "display_name": manifest.get("displayName", item.name),
                        "version": manifest.get("version", "1.0.0"),
                        "description": manifest.get("description", ""),
                        "author": manifest.get("author", {}).get("name", "Unknown") if isinstance(manifest.get("author"), dict) else manifest.get("author", "Unknown"),
                        "location": str(item),
                        "manifest_path": str(manifest_file) if manifest_file.is_file() else None,
                        "skills_count": len(exposed_skills),
                        "skills": exposed_skills,
                        "subagents": exposed_agents,
                        "has_mcp": (item / "mcp_config.json").is_file(),
                        "has_hooks": (item / "hooks.json").is_file(),
                        "has_rules": (item / "rules").is_dir()
                    })
                    seen.add(item.name)

        return sorted(plugins, key=lambda p: p["name"])

    def get_plugin_details(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Returns complete plugin information, including manifest, rules, and components."""
        plugins = self.list_plugins()
        plugin = next((p for p in plugins if p["name"] == plugin_name), None)
        if not plugin:
            return None

        pdir = Path(plugin["location"])
        
        # Read rules
        rules = []
        rules_dir = pdir / "rules"
        if rules_dir.is_dir():
            for r in rules_dir.glob("*.md"):
                rules.append({
                    "name": r.stem,
                    "filename": r.name,
                    "path": str(r),
                    "content": r.read_text(encoding="utf-8", errors="replace")
                })

        # Read MCP config if present
        mcp_config = None
        mcp_file = pdir / "mcp_config.json"
        if mcp_file.is_file():
            try:
                mcp_config = json.loads(mcp_file.read_text(encoding="utf-8"))
            except Exception:
                mcp_config = None

        return {
            **plugin,
            "rules": rules,
            "mcp_config": mcp_config
        }

    # -------------------------------------------------------------------------
    # RULES DISCOVERY
    # -------------------------------------------------------------------------

    def list_rules(self) -> List[Dict[str, Any]]:
        """Discovers all active rules across workspace and global configurations."""
        rules = []

        # 1. Workspace Rules
        # Top-level GEMINI.md or AGENTS.md
        for top_file in ["GEMINI.md", "AGENTS.md"]:
            fp = self.workspace_root / top_file
            if fp.is_file():
                rules.append({
                    "name": top_file,
                    "scope": "workspace",
                    "path": str(fp),
                    "trigger": "always_on",
                    "preview": fp.read_text(encoding="utf-8", errors="replace")[:300]
                })

        # .agents/rules/*.md
        ws_rules_dir = self.workspace_agents_dir / "rules"
        if ws_rules_dir.is_dir():
            for r in ws_rules_dir.glob("*.md"):
                content = r.read_text(encoding="utf-8", errors="replace")
                trigger = "always_on" if "always_on" in content else "model_decision"
                rules.append({
                    "name": r.name,
                    "scope": "workspace",
                    "path": str(r),
                    "trigger": trigger,
                    "preview": content[:300]
                })

        # 2. Global Rules (~/.gemini/config/rules/*.md or GEMINI.md)
        global_rules_dir = self.global_config_dir / "rules"
        if global_rules_dir.is_dir():
            for r in global_rules_dir.glob("*.md"):
                content = r.read_text(encoding="utf-8", errors="replace")
                rules.append({
                    "name": r.name,
                    "scope": "global",
                    "path": str(r),
                    "trigger": "always_on" if "always_on" in content else "model_decision",
                    "preview": content[:300]
                })

        return rules

    def get_rule_content(self, rule_identifier: str) -> Optional[Dict[str, Any]]:
        """Reads the full content of a rule by name or file path."""
        p = Path(rule_identifier)
        if p.is_file():
            return {
                "name": p.name,
                "path": str(p),
                "content": p.read_text(encoding="utf-8", errors="replace")
            }
            
        rules = self.list_rules()
        for r in rules:
            if r["name"] == rule_identifier or Path(r["path"]).stem == rule_identifier:
                content = Path(r["path"]).read_text(encoding="utf-8", errors="replace")
                return {
                    "name": r["name"],
                    "path": r["path"],
                    "content": content
                }
        return None

    # -------------------------------------------------------------------------
    # CONVERSATIONS & ARTIFACTS INSPECTION
    # -------------------------------------------------------------------------

    def list_conversations(self) -> List[Dict[str, Any]]:
        """Lists recent conversations from the Antigravity brain directory."""
        conversations = []
        if not self.brain_dir.is_dir():
            return conversations

        for item in self.brain_dir.iterdir():
            if item.is_dir() and item.name != "scratch":
                conv_id = item.name
                log_file = item / ".system_generated" / "logs" / "transcript.jsonl"
                artifacts_count = len(list(item.glob("*.md")))
                
                # Check modification time
                mtime = item.stat().st_mtime
                conversations.append({
                    "conversation_id": conv_id,
                    "modified_timestamp": mtime,
                    "modified_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
                    "has_transcript": log_file.is_file(),
                    "artifacts_count": artifacts_count,
                    "path": str(item)
                })

        return sorted(conversations, key=lambda c: c["modified_timestamp"], reverse=True)

    def get_conversation_transcript(self, conversation_id: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """Reads transcript events (steps, user inputs, planner responses, tool calls)."""
        if not conversation_id:
            convs = self.list_conversations()
            if not convs:
                return {"error": "No conversations found"}
            conversation_id = convs[0]["conversation_id"]

        transcript_file = self.brain_dir / conversation_id / ".system_generated" / "logs" / "transcript.jsonl"
        if not transcript_file.is_file():
            return {"conversation_id": conversation_id, "error": f"Transcript file not found at {transcript_file}"}

        events = []
        try:
            with open(transcript_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            step_idx = data.get("step_index")
                            step_type = data.get("type")
                            source = data.get("source")
                            content = data.get("content", "")
                            tool_calls = data.get("tool_calls", [])
                            
                            # Condense content for readable summary
                            summary = {
                                "step": step_idx,
                                "type": step_type,
                                "source": source,
                                "tool_calls": [t.get("name") for t in tool_calls if isinstance(t, dict)] if tool_calls else []
                            }
                            if step_type == "USER_INPUT":
                                summary["user_prompt"] = content[:300]
                            elif content:
                                summary["content_preview"] = content[:200]
                                
                            events.append(summary)
                        except Exception:
                            pass
        except Exception as e:
            return {"conversation_id": conversation_id, "error": str(e)}

        return {
            "conversation_id": conversation_id,
            "total_steps": len(events),
            "recent_events": events[-limit:] if limit > 0 else events
        }

    def list_artifacts(self, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists artifacts stored in the specified or active conversation directory."""
        if not conversation_id:
            convs = self.list_conversations()
            if not convs:
                return []
            conversation_id = convs[0]["conversation_id"]

        conv_dir = self.brain_dir / conversation_id
        if not conv_dir.is_dir():
            return []

        artifacts = []
        for f in conv_dir.glob("*.md"):
            artifacts.append({
                "name": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))
            })
        return artifacts

    def read_artifact(self, artifact_name_or_path: str, conversation_id: Optional[str] = None) -> Optional[str]:
        """Reads an artifact file content."""
        p = Path(artifact_name_or_path)
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")
            
        if not conversation_id:
            convs = self.list_conversations()
            if convs:
                conversation_id = convs[0]["conversation_id"]
                
        if conversation_id:
            cand = self.brain_dir / conversation_id / artifact_name_or_path
            if cand.is_file():
                return cand.read_text(encoding="utf-8", errors="replace")
        return None

    # -------------------------------------------------------------------------
    # COMMAND & AGENT ORCHESTRATION
    # -------------------------------------------------------------------------

    def execute_command(self, command: str, cwd: Optional[str] = None, timeout: int = 45) -> Dict[str, Any]:
        """Executes a command safely within the target directory."""
        target_cwd = cwd or str(self.workspace_root)
        start_time = time.time()
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=target_cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            duration = round(time.time() - start_time, 3)
            return {
                "command": command,
                "cwd": target_cwd,
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "duration_seconds": duration,
                "success": res.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "command": command,
                "cwd": target_cwd,
                "exit_code": -1,
                "error": f"Command timed out after {timeout} seconds",
                "success": False
            }
        except Exception as e:
            return {
                "command": command,
                "cwd": target_cwd,
                "exit_code": -1,
                "error": str(e),
                "success": False
            }

    def create_skill(self, name: str, description: str, instructions: str, scope: str = "workspace") -> Dict[str, Any]:
        """Creates a new Antigravity skill adhering strictly to specification."""
        clean_name = re.sub(r"[^a-z0-9\-]", "-", name.lower()).strip("-")
        
        if scope == "global":
            target_dir = self.global_config_dir / "skills" / clean_name
        else:
            target_dir = self.workspace_agents_dir / "skills" / clean_name
            
        target_dir.mkdir(parents=True, exist_ok=True)
        skill_file = target_dir / "SKILL.md"

        content = f"""---
name: {clean_name}
description: >-
  {description.strip()}
---

# {name.replace('-', ' ').title()}

{instructions.strip()}
"""
        skill_file.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "name": clean_name,
            "path": str(target_dir),
            "skill_file": str(skill_file)
        }

    def create_rule(self, filename: str, content: str, scope: str = "workspace", trigger: str = "always_on") -> Dict[str, Any]:
        """Creates or updates a rule in .agents/rules or global config."""
        clean_file = filename if filename.endswith(".md") else f"{filename}.md"
        
        if scope == "global":
            target_dir = self.global_config_dir / "rules"
        else:
            target_dir = self.workspace_agents_dir / "rules"
            
        target_dir.mkdir(parents=True, exist_ok=True)
        rule_file = target_dir / clean_file
        
        rule_content = f"""<!--
trigger: {trigger}
-->

{content.strip()}
"""
        rule_file.write_text(rule_content, encoding="utf-8")
        return {
            "success": True,
            "filename": clean_file,
            "path": str(rule_file)
        }
