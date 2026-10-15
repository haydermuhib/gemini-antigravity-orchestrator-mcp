"""
MCP Resources Provider for Antigravity.
Allows clients to read state, skills catalogs, and workspace configs as URI resources.
"""

import json
from typing import Dict, List, Any, Optional
from .antigravity_engine import AntigravityEngine


def get_resource_definitions() -> List[Dict[str, Any]]:
    return [
        {
            "uri": "antigravity://status",
            "name": "Antigravity IDE Status",
            "description": "Live snapshot of the Antigravity IDE, paths, and total customization counts.",
            "mimeType": "application/json"
        },
        {
            "uri": "antigravity://skills/catalog",
            "name": "Skills Catalog",
            "description": "Catalog of all discovered global, workspace, and plugin skills.",
            "mimeType": "application/json"
        },
        {
            "uri": "antigravity://plugins/catalog",
            "name": "Plugins Catalog",
            "description": "List and manifest summary of all installed plugins.",
            "mimeType": "application/json"
        },
        {
            "uri": "antigravity://rules/active",
            "name": "Active Rules",
            "description": "List of active rules loaded for the current workspace and globally.",
            "mimeType": "application/json"
        },
        {
            "uri": "antigravity://conversations/recent",
            "name": "Recent Conversations",
            "description": "Recent conversations and generated artifacts in the Antigravity brain.",
            "mimeType": "application/json"
        }
    ]


def read_resource_content(engine: AntigravityEngine, uri: str) -> Optional[Dict[str, Any]]:
    if uri == "antigravity://status":
        data = engine.get_ide_status()
        return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(data, indent=2)}]}
        
    elif uri == "antigravity://skills/catalog":
        data = engine.list_skills(scope="all")
        return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(data, indent=2)}]}
        
    elif uri == "antigravity://plugins/catalog":
        data = engine.list_plugins()
        return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(data, indent=2)}]}
        
    elif uri == "antigravity://rules/active":
        data = engine.list_rules()
        return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(data, indent=2)}]}
        
    elif uri == "antigravity://conversations/recent":
        data = engine.list_conversations()
        return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(data, indent=2)}]}
        
    return None
