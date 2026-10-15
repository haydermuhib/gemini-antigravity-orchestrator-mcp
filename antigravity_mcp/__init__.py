"""
Antigravity MCP Package - Model Context Protocol Server for Google Gemini & Antigravity IDE Orchestration.
"""

from .antigravity_engine import AntigravityEngine
from .server import MCPServer

__version__ = "1.0.1"
__all__ = ["AntigravityEngine", "MCPServer", "__version__"]
