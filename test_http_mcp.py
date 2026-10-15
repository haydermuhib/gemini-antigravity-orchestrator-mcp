#!/usr/bin/env python3
"""
Test HTTP / SSE endpoints for Google Gemini MCP compatibility.
"""

import sys
import time
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path


def run_http_tests():
    project_root = Path(__file__).resolve().parent
    server_path = project_root / "server.py"

    print("🚀 Starting Antigravity MCP Server in HTTP mode on port 8999...")
    proc = subprocess.Popen(
        [sys.executable, str(server_path), "--http", "--port", "8999", "--workspace", str(project_root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    time.sleep(1.0)
    base_url = "http://127.0.0.1:8999"

    try:
        # 1. Test GET / (Health & Info)
        print("1. Testing GET / (Server Info)...")
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "online"
            print("  ✅ GET / returned status online:", data["name"])

        # 2. Test POST / with JSON-RPC initialize
        print("2. Testing POST / initialize...")
        init_body = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "google-gemini", "version": "1.0"}
            }
        }).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/", data=init_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data["result"]["serverInfo"]["name"] == "antigravity-mcp-orchestrator"
            print("  ✅ POST / initialize succeeded.")

        # 3. Test POST / tools/list
        print("3. Testing POST / tools/list...")
        list_body = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/", data=list_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tools = data["result"]["tools"]
            print(f"  ✅ POST / tools/list returned {len(tools)} tools.")
            assert len(tools) >= 16

        # 4. Test POST / tools/call for search_skills
        print("4. Testing POST / tools/call (search_skills)...")
        call_body = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_skills",
                "arguments": {"query": "bento"}
            }
        }).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/", data=call_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = json.loads(data["result"]["content"][0]["text"])
            assert any(s["name"] == "bento" for s in content)
            print("  ✅ POST / tools/call returned matching skills.")

        # 5. Test SSE initial event
        print("5. Testing GET /sse...")
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", 8999, timeout=5)
        conn.request("GET", "/sse", headers={"Accept": "text/event-stream"})
        resp = conn.getresponse()
        first_line = resp.readline().decode("utf-8")
        second_line = resp.readline().decode("utf-8")
        conn.close()
        print(f"  Received SSE stream: {first_line.strip()} | {second_line.strip()}")
        assert "event: endpoint" in first_line
        assert "/message?sessionId=" in second_line
        print("  ✅ SSE handshake passed successfully.")

        # 6. Test OAuth 2.0 Well-Known Discovery
        print("6. Testing OAuth Discovery (/.well-known/oauth-authorization-server)...")
        req = urllib.request.Request(f"{base_url}/.well-known/oauth-authorization-server")
        with urllib.request.urlopen(req) as resp:
            oauth_disco = json.loads(resp.read().decode("utf-8"))
            assert "/oauth/authorize" in oauth_disco["authorization_endpoint"]
            assert "/oauth/token" in oauth_disco["token_endpoint"]
            print("  ✅ OAuth discovery endpoint succeeded.")

        # 7. Test OAuth 2.0 Token Exchange
        print("7. Testing OAuth Token Exchange (POST /oauth/token)...")
        token_body = json.dumps({
            "grant_type": "authorization_code",
            "code": "antigravity_sample_code",
            "client_id": "gemini-client-id",
            "client_secret": "gemini-client-secret"
        }).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/oauth/token", data=token_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            token_res = json.loads(resp.read().decode("utf-8"))
            assert "access_token" in token_res
            assert token_res["token_type"] == "Bearer"
            print("  ✅ OAuth token exchange succeeded:", token_res["token_type"])

        # 8. Test HEAD /sse (Gemini pre-flight probe)
        print("8. Testing HEAD /sse (Gemini pre-flight probe)...")
        conn = http.client.HTTPConnection("127.0.0.1", 8999, timeout=5)
        conn.request("HEAD", "/sse")
        head_resp = conn.getresponse()
        assert head_resp.status == 200
        conn.close()
        print("  ✅ HEAD /sse returned 200 OK.")

        # 10. Test Static Branding Assets (Favicon & Connector Logo)
        print("10. Testing Static Branding Assets (/favicon.ico & /logo.png)...")
        with urllib.request.urlopen(f"{base_url}/favicon.ico") as resp:
            assert resp.status == 200
            assert resp.headers.get("Content-Type") == "image/x-icon"
            print("  ✅ /favicon.ico served successfully.")
        with urllib.request.urlopen(f"{base_url}/logo.png") as resp:
            assert resp.status == 200
            assert resp.headers.get("Content-Type") == "image/png"
            print("  ✅ /logo.png served successfully.")

        print("\n🎉 ALL HTTP, SSE, HEAD, OAUTH 2.0 & BRANDING TESTS PASSED!")

    finally:
        proc.terminate()


if __name__ == "__main__":
    run_http_tests()
