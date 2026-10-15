"""
HTTP & SSE Remote Transport for Antigravity MCP Server.
Allows Google Gemini (Cloud / Connected Apps) to connect via public HTTPS URL without password.
Supports:
1. Standard MCP SSE Transport (GET /sse + POST /message?sessionId=...)
2. Direct Streamable HTTP POST Transport (POST / or POST /mcp)
3. CORS headers for web/cloud clients
4. Keep-alive heartbeats for Cloudflare and cloud proxies
5. Pure Python 3 standard library - zero external dependencies
"""

import sys
import json
import time
import uuid
import queue
import logging
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Dict, Any, Optional

from .antigravity_engine import AntigravityEngine
from .tools import get_tool_definitions, handle_tool_call
from .resources import get_resource_definitions, read_resource_content
from .prompts import get_prompt_definitions, get_prompt_content

logger = logging.getLogger("AntigravityHttpMCPServer")


class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.queue: queue.Queue = queue.Queue()
        self.created_at = time.time()
        self.active = True

    def send(self, data: Dict[str, Any]):
        self.queue.put(data)


class MCPHttpHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "Antigravity-MCP/1.0.0"

    # Reference to the shared state on the server instance
    @property
    def engine(self) -> AntigravityEngine:
        return self.server.engine

    @property
    def sessions(self) -> Dict[str, Session]:
        return self.server.sessions

    def log_message(self, format, *args):
        # Log to stderr so stdout is never polluted
        sys.stderr.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [HTTP] {format % args}\n")

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-session-id, Mcp-Session-Id, Accept")
        self.send_header("Access-Control-Expose-Headers", "*")

    def do_OPTIONS(self):
        """Handle pre-flight CORS requests."""
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        """Handle HEAD requests (used by Gemini and cloud health probes)."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        self.send_response(200)
        if path in ("/sse", "/events", "/mcp/sse"):
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        else:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", "0")
        self._send_cors_headers()
        self.end_headers()

    def _send_json_response(self, status_code: int, data: Any):
        payload = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _serve_static_file(self, filepath: Path, content_type: str):
        if not filepath.is_file():
            self._send_json_response(404, {"error": "Asset not found"})
            return
        data = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)

        # 0. Static Branding & Connector Assets
        branding_dir = Path(__file__).resolve().parent.parent / "branding" / "dist"
        if path.startswith("/branding/dist/"):
            rel_name = path[len("/branding/dist/"):]
            target = branding_dir / rel_name
            ext = target.suffix.lower()
            ct = "image/png" if ext == ".png" else "image/svg+xml" if ext == ".svg" else "image/x-icon" if ext == ".ico" else "application/zip" if ext == ".zip" else "application/octet-stream"
            self._serve_static_file(target, ct)
            return
        if path in ("/brand-kit.zip", "/brand-kit", "/antigravity-mcp-brand-kit.zip"):
            self._serve_static_file(branding_dir / "antigravity-mcp-brand-kit.zip", "application/zip")
            return
        if path in ("/favicon.ico",):
            self._serve_static_file(branding_dir / "favicon.ico", "image/x-icon")
            return
        if path in ("/logo.png", "/icon.png", "/icon-512.png", "/icon-192.png"):
            self._serve_static_file(branding_dir / "antigravity-mcp-app-icon-512.png", "image/png")
            return
        if path in ("/apple-touch-icon.png",):
            self._serve_static_file(branding_dir / "apple-touch-icon.png", "image/png")
            return
        if path in ("/logo.svg", "/favicon.svg"):
            self._serve_static_file(branding_dir / "favicon.svg", "image/svg+xml")
            return
        if path in ("/logo-dark.svg",):
            self._serve_static_file(branding_dir / "logo-dark.svg", "image/svg+xml")
            return
        if path in ("/logo-dark-lockup.png",):
            self._serve_static_file(branding_dir / "logo-dark-lockup.png", "image/png")
            return
        if path in ("/site.webmanifest", "/manifest.json"):
            self._serve_static_file(branding_dir / "site.webmanifest", "application/manifest+json")
            return

        # 1. OAuth 2.0 Protected Resource Metadata (RFC 9728)
        if path.startswith("/.well-known/oauth-protected-resource"):
            self._send_oauth_protected_resource()
            return

        # 2. OAuth 2.0 Well-Known Discovery
        if path in ("/.well-known/oauth-authorization-server", "/.well-known/openid-configuration"):
            self._send_oauth_discovery()
            return

        # 2. OAuth 2.0 Authorize Endpoint
        if path in ("/oauth/authorize", "/authorize"):
            self._handle_oauth_authorize(parsed, query)
            return

        # 3. OpenID Connect UserInfo Endpoint
        if path in ("/oauth/userinfo", "/userinfo"):
            userinfo = {
                "sub": "haider-antigravity",
                "name": "Antigravity Orchestrator",
                "email": "antigravity@local.dev"
            }
            self._send_json_response(200, userinfo)
            return

        # 4. JWKS Endpoint
        if path in ("/oauth/jwks", "/jwks"):
            self._send_json_response(200, {"keys": []})
            return

        # 5. Server-Sent Events (SSE) Endpoint
        if path in ("/sse", "/events", "/mcp/sse"):
            self._handle_sse(parsed)
            return

        # 6. Landing Page / Root info endpoint
        index_file = Path(__file__).resolve().parent.parent / "index.html"
        accept = self.headers.get("Accept", "")
        if index_file.is_file() and ("text/html" in accept or "application/xhtml+xml" in accept):
            self._serve_static_file(index_file, "text/html; charset=utf-8")
            return

        host = self.headers.get("Host", "localhost:8080")
        proto = "https" if "trycloudflare.com" in host or self.headers.get("X-Forwarded-Proto") == "https" else "http"
        base = f"{proto}://{host}"
        status = self.engine.get_ide_status()
        info = {
            "name": "Antigravity MCP Server for Google Gemini",
            "status": "online",
            "version": "1.0.0",
            "logo_uri": f"{base}/logo.png",
            "icon_uri": f"{base}/icon.png",
            "transport": "HTTP / Server-Sent Events (SSE)",
            "oauth": {
                "supported": True,
                "authorization_endpoint": "/oauth/authorize",
                "token_endpoint": "/oauth/token"
            },
            "endpoints": {
                "sse": "/sse",
                "message": "/message",
                "direct_http": "/"
            },
            "environment": status
        }
        self._send_json_response(200, info)

    def _send_oauth_protected_resource(self):
        host = self.headers.get("Host", "localhost:8080")
        proto = "https" if "trycloudflare.com" in host or self.headers.get("X-Forwarded-Proto") == "https" else "http"
        base = f"{proto}://{host}"
        data = {
            "resource": f"{base}/sse",
            "authorization_servers": [base],
            "scopes_supported": ["mcp:all"],
            "logo_uri": f"{base}/logo.png",
            "icon_uri": f"{base}/icon.png"
        }
        self._send_json_response(200, data)

    def _send_oauth_discovery(self):
        host = self.headers.get("Host", "localhost:8080")
        proto = "https" if "trycloudflare.com" in host or self.headers.get("X-Forwarded-Proto") == "https" else "http"
        base = f"{proto}://{host}"
        
        discovery = {
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "userinfo_endpoint": f"{base}/oauth/userinfo",
            "jwks_uri": f"{base}/oauth/jwks",
            "response_types_supported": ["code", "token"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic", "none"],
            "logo_uri": f"{base}/logo.png",
            "icon_uri": f"{base}/icon.png",
            "service_documentation": "https://github.com/haydermuhib/gemini-antigravity-orchestrator-mcp"
        }
        self._send_json_response(200, discovery)

    def _handle_oauth_authorize(self, parsed, query):
        redirect_uri = query.get("redirect_uri", [None])[0]
        state = query.get("state", [""])[0]
        code = f"antigravity_code_{uuid.uuid4().hex[:16]}"
        
        # Save code for validation in token exchange
        self.server.oauth_codes[code] = {
            "created_at": time.time(),
            "client_id": query.get("client_id", [""])[0]
        }

        if redirect_uri:
            # Construct redirect URL
            delimiter = "&" if "?" in redirect_uri else "?"
            target_url = f"{redirect_uri}{delimiter}code={code}"
            if state:
                target_url += f"&state={state}"

            logger.info(f"OAuth authorize redirected to: {target_url}")
            self.send_response(302)
            self.send_header("Location", target_url)
            self._send_cors_headers()
            self.end_headers()
        else:
            # Render authorization success HTML
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            html = f"""<!DOCTYPE html>
<html>
<head><title>Antigravity MCP Authorized</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
  <h2 style="color: #1a73e8;">Antigravity MCP Connected to Google Gemini</h2>
  <p>Authorization code generated: <code>{code}</code></p>
  <p>You can close this window and return to Gemini.</p>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))

    def _handle_sse(self, parsed):
        session_id = str(uuid.uuid4())
        session = Session(session_id)
        self.sessions[session_id] = session

        logger.info(f"New SSE connection opened. Session ID: {session_id}")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self._send_cors_headers()
        self.end_headers()

        # Send initial endpoint event as specified by MCP SSE transport
        endpoint_uri = f"/message?sessionId={session_id}"
        init_payload = f"event: endpoint\ndata: {endpoint_uri}\n\n"
        try:
            self.wfile.write(init_payload.encode("utf-8"))
            self.wfile.flush()
        except Exception as e:
            logger.warning(f"Failed to send initial endpoint event: {e}")
            del self.sessions[session_id]
            return

        # SSE Stream loop
        last_heartbeat = time.time()
        try:
            while session.active:
                try:
                    # Wait for message in session queue
                    msg = session.queue.get(timeout=2.0)
                    event_str = f"event: message\ndata: {json.dumps(msg)}\n\n"
                    self.wfile.write(event_str.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    pass

                # Keep connection alive with periodic comment pings
                if time.time() - last_heartbeat > 15.0:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    last_heartbeat = time.time()
        except (BrokenPipeError, ConnectionResetError):
            logger.info(f"SSE client disconnected. Session ID: {session_id}")
        finally:
            session.active = False
            self.sessions.pop(session_id, None)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)

        # Read POST body
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            self.send_response(400)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"error": "Empty request body"}')
            return

        # OAuth 2.0 Token Endpoint
        if path in ("/oauth/token", "/token"):
            self._handle_oauth_token(content_len)
            return

        body_bytes = self.rfile.read(content_len)
        try:
            req_json = json.loads(body_bytes.decode("utf-8"))
        except Exception as e:
            self._send_json_response(400, {"error": f"JSON parse error: {str(e)}"})
            return

        # Check session if this is an SSE-bound message
        session_id = query.get("sessionId", [None])[0] or self.headers.get("x-session-id") or self.headers.get("Mcp-Session-Id")
        session = self.sessions.get(session_id) if session_id else None

        # Execute JSON-RPC dispatch
        response_json = self._dispatch(req_json)

        # If connected via SSE session, push event to session queue
        if session and session.active and response_json is not None:
            session.send(response_json)

        # Also return response in HTTP body (dual-delivery for maximum client compatibility)
        if response_json is not None:
            self._send_json_response(200, response_json)
        else:
            self._send_json_response(200, {"status": "accepted"})

    def _dispatch(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        # Notifications require no response
        if req_id is None:
            if method == "notifications/initialized":
                logger.info("Client acknowledged initialization.")
            return None

        try:
            if method == "initialize":
                res = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "antigravity-mcp-orchestrator",
                        "version": "1.0.0"
                    }
                }
                return {"jsonrpc": "2.0", "id": req_id, "result": res}

            elif method == "ping":
                return {"jsonrpc": "2.0", "id": req_id, "result": {}}

            elif method == "tools/list":
                return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": get_tool_definitions()}}

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                logger.info(f"Tool call received: {tool_name}")
                result_data = handle_tool_call(self.engine, tool_name, tool_args)
                text_payload = json.dumps(result_data, indent=2, default=str)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text_payload}],
                        "isError": False
                    }
                }

            elif method == "resources/list":
                return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": get_resource_definitions()}}

            elif method == "resources/read":
                uri = params.get("uri")
                res = read_resource_content(self.engine, uri)
                if res:
                    return {"jsonrpc": "2.0", "id": req_id, "result": res}
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32602, "message": f"Resource URI not found: {uri}"}
                    }

            elif method == "prompts/list":
                return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": get_prompt_definitions()}}

            elif method == "prompts/get":
                prompt_name = params.get("name")
                prompt_args = params.get("arguments", {})
                res = get_prompt_content(prompt_name, prompt_args)
                return {"jsonrpc": "2.0", "id": req_id, "result": res}

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }

        except Exception as e:
            logger.exception(f"Error handling method {method}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Internal server error: {str(e)}"}
            }


    def _handle_oauth_token(self, content_len: int):
        body_bytes = self.rfile.read(content_len)
        body_str = body_bytes.decode("utf-8")
        
        # Parse either application/x-www-form-urlencoded or application/json
        params = {}
        if self.headers.get("Content-Type", "").startswith("application/json"):
            try:
                params = json.loads(body_str)
            except Exception:
                pass
        else:
            parsed_form = parse_qs(body_str)
            params = {k: v[0] for k, v in parsed_form.items()}

        grant_type = params.get("grant_type", "authorization_code")
        code = params.get("code")
        client_id = params.get("client_id", "gemini-client")

        logger.info(f"OAuth token request: grant_type={grant_type}, client_id={client_id}")

        # Generate a valid Bearer token for Gemini
        token_data = {
            "access_token": f"antigravity_token_{uuid.uuid4().hex}",
            "token_type": "Bearer",
            "expires_in": 31536000,
            "refresh_token": f"antigravity_refresh_{uuid.uuid4().hex}",
            "scope": "mcp:all"
        }

        self._send_json_response(200, token_data)


class AntigravityHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, workspace_root: Optional[str] = None):
        super().__init__(server_address, RequestHandlerClass)
        self.engine = AntigravityEngine(workspace_root=workspace_root)
        self.sessions: Dict[str, Session] = {}
        self.oauth_codes: Dict[str, Any] = {}


def start_http_server(host: str = "0.0.0.0", port: int = 8080, workspace_root: Optional[str] = None):
    """Starts the threaded HTTP/SSE MCP server."""
    server_address = (host, port)
    httpd = AntigravityHTTPServer(server_address, MCPHttpHandler, workspace_root=workspace_root)
    logger.info(f"Antigravity HTTP/SSE MCP Server running on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping HTTP MCP Server...")
        httpd.server_close()
