"""
Antigravity MCP Package - Model Context Protocol Server for Google Gemini & Antigravity IDE Orchestration.
"""

from .antigravity_engine import AntigravityEngine
from .server import MCPServer

__version__ = "1.0.0"
__all__ = ["AntigravityEngine", "MCPServer"]
