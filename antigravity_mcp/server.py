"""
Standard-compliant Model Context Protocol (MCP) JSON-RPC 2.0 Stdio Server.
Zero external dependencies - runs on any Python 3.10+ standard installation.
"""

import sys
import json
import logging
from typing import Dict, Any, Optional

from .antigravity_engine import AntigravityEngine
from .tools import get_tool_definitions, handle_tool_call
from .resources import get_resource_definitions, read_resource_content
from .prompts import get_prompt_definitions, get_prompt_content

# Configure stderr logging so stdout remains clean JSON-RPC only
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AntigravityMCP] %(message)s"
)
logger = logging.getLogger("AntigravityMCPServer")


class MCPServer:
    def __init__(self, workspace_root: Optional[str] = None):
        self.engine = AntigravityEngine(workspace_root=workspace_root)
        self.protocol_version = "2024-11-05"
        self.server_info = {
            "name": "antigravity-mcp-orchestrator",
            "version": "1.0.0"
        }

    def run(self):
        """Main stdio loop reading JSON-RPC requests line by line."""
        logger.info("Antigravity MCP Server started. Listening on stdio...")
        for line in sys.stdin:
            line_str = line.strip()
            if not line_str:
                continue

            try:
                request = json.loads(line_str)
            except Exception as e:
                self._send_error(None, -32700, f"Parse error: {str(e)}")
                continue

            self._dispatch(request)

    def _dispatch(self, req: Dict[str, Any]):
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        # Handle notifications (requests without an ID)
        if req_id is None:
            if method == "notifications/initialized":
                logger.info("Client acknowledged initialization.")
            return

        try:
            if method == "initialize":
                res = {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False}
                    },
                    "serverInfo": self.server_info
                }
                self._send_result(req_id, res)

            elif method == "ping":
                self._send_result(req_id, {})

            elif method == "tools/list":
                self._send_result(req_id, {"tools": get_tool_definitions()})

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                logger.info(f"Executing tool call: {tool_name}")
                result_data = handle_tool_call(self.engine, tool_name, tool_args)
                
                # Format into MCP standard content structure
                text_payload = json.dumps(result_data, indent=2, default=str)
                self._send_result(req_id, {
                    "content": [
                        {
                            "type": "text",
                            "text": text_payload
                        }
                    ],
                    "isError": False
                })

            elif method == "resources/list":
                self._send_result(req_id, {"resources": get_resource_definitions()})

            elif method == "resources/read":
                uri = params.get("uri")
                res = read_resource_content(self.engine, uri)
                if res:
                    self._send_result(req_id, res)
                else:
                    self._send_error(req_id, -32602, f"Resource URI not found: {uri}")

            elif method == "prompts/list":
                self._send_result(req_id, {"prompts": get_prompt_definitions()})

            elif method == "prompts/get":
                prompt_name = params.get("name")
                prompt_args = params.get("arguments", {})
                res = get_prompt_content(prompt_name, prompt_args)
                self._send_result(req_id, res)

            else:
                self._send_error(req_id, -32601, f"Method not found: {method}")

        except Exception as e:
            logger.exception(f"Error handling method {method}")
            self._send_error(req_id, -32603, f"Internal server error: {str(e)}")

    def _send_result(self, req_id: Any, result: Any):
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    def _send_error(self, req_id: Any, code: int, message: str):
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
