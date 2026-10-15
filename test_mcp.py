#!/usr/bin/env python3
"""
Test Suite for Antigravity MCP Server.
Simulates a real MCP client (like Google Gemini) talking to the server over stdio.
"""

import sys
import json
import subprocess
from pathlib import Path


def run_tests():
    project_root = Path(__file__).resolve().parent
    server_path = project_root / "server.py"

    print("🚀 Starting Antigravity MCP Server test run...")
    proc = subprocess.Popen(
        [sys.executable, str(server_path), "--workspace", str(project_root)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    req_id = 1

    def send_request(req):
        nonlocal req_id
        req["id"] = req_id
        req_id += 1
        payload = json.dumps(req) + "\n"
        proc.stdin.write(payload)
        proc.stdin.flush()
        res_line = proc.stdout.readline()
        if not res_line:
            err = proc.stderr.read()
            raise RuntimeError(f"Server closed connection unexpectedly. Stderr: {err}")
        return json.loads(res_line.strip())

    # 1. Initialize
    print("Testing 'initialize'...")
    init_res = send_request({
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "google-gemini", "version": "1.0"}
        }
    })
    assert "result" in init_res, f"Init failed: {init_res}"
    assert init_res["result"]["serverInfo"]["name"] == "antigravity-mcp-orchestrator"
    print("  ✅ 'initialize' passed successfully.")

    # 2. Notification initialized
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
    proc.stdin.flush()

    # 3. List Tools
    print("Testing 'tools/list'...")
    tools_res = send_request({"jsonrpc": "2.0", "method": "tools/list", "params": {}})
    tools = tools_res["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    print(f"  Discovered {len(tools)} tools: {', '.join(tool_names[:6])}...")
    assert "get_antigravity_status" in tool_names
    assert "list_skills" in tool_names
    assert "search_skills" in tool_names
    assert "list_plugins" in tool_names
    assert "orchestrate_agent_workflow" in tool_names
    print("  ✅ 'tools/list' passed successfully.")

    # 4. Call get_antigravity_status
    print("Testing tool call 'get_antigravity_status'...")
    status_res = send_request({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "get_antigravity_status", "arguments": {}}
    })
    content_text = status_res["result"]["content"][0]["text"]
    status_data = json.loads(content_text)
    print(f"  Antigravity IDE status: {status_data['counts']}")
    assert status_data["counts"]["total_skills"] > 0
    print("  ✅ 'get_antigravity_status' passed successfully.")

    # 4b. Call list_known_workspaces
    print("Testing tool call 'list_known_workspaces'...")
    ws_res = send_request({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "list_known_workspaces", "arguments": {}}
    })
    ws_list = json.loads(ws_res["result"]["content"][0]["text"])
    print(f"  Discovered {len(ws_list)} workspaces. Active: {[w['name'] for w in ws_list if w['is_active']]}")
    assert len(ws_list) > 0
    print("  ✅ 'list_known_workspaces' passed successfully.")

    # 4c. Call set_active_workspace
    print("Testing tool call 'set_active_workspace'...")
    switch_res = send_request({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "set_active_workspace", "arguments": {"workspace_path": str(project_root)}}
    })
    switch_data = json.loads(switch_res["result"]["content"][0]["text"])
    assert switch_data["success"] is True
    print("  ✅ 'set_active_workspace' passed successfully.")

    # 5. Call search_skills
    print("Testing tool call 'search_skills'...")
    search_res = send_request({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "search_skills", "arguments": {"query": "bento grid layout"}}
    })
    skills_found = json.loads(search_res["result"]["content"][0]["text"])
    print(f"  Found {len(skills_found)} matching skills. Top: {skills_found[0]['name']}")
    assert any(s["name"] == "bento" for s in skills_found)
    print("  ✅ 'search_skills' passed successfully.")

    # 6. Call get_skill
    print("Testing tool call 'get_skill' for 'bento'...")
    skill_res = send_request({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "get_skill", "arguments": {"skill_name": "bento"}}
    })
    skill_data = json.loads(skill_res["result"]["content"][0]["text"])
    assert "full_content" in skill_data
    assert "bento" in skill_data["name"]
    print("  ✅ 'get_skill' passed successfully.")

    # 7. Call list_plugins
    print("Testing tool call 'list_plugins'...")
    plugins_res = send_request({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "list_plugins", "arguments": {}}
    })
    plugins_list = json.loads(plugins_res["result"]["content"][0]["text"])
    plugin_names = [p["name"] for p in plugins_list]
    print(f"  Discovered plugins: {plugin_names}")
    assert "cursor-team-kit" in plugin_names
    print("  ✅ 'list_plugins' passed successfully.")

    # 8. Call orchestrate_agent_workflow
    print("Testing tool call 'orchestrate_agent_workflow'...")
    orch_res = send_request({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "orchestrate_agent_workflow",
            "arguments": {
                "task": "Create a high-impact dashboard interface",
                "preferred_aesthetic": "bento"
            }
        }
    })
    orch_data = json.loads(orch_res["result"]["content"][0]["text"])
    assert "orchestration_workflow" in orch_data
    print(f"  Orchestration workflow phases: {len(orch_data['orchestration_workflow'])}")
    print("  ✅ 'orchestrate_agent_workflow' passed successfully.")

    # 9. Test Resources
    print("Testing 'resources/list' and 'resources/read'...")
    res_list = send_request({"jsonrpc": "2.0", "method": "resources/list", "params": {}})
    uris = [r["uri"] for r in res_list["result"]["resources"]]
    assert "antigravity://status" in uris
    
    res_read = send_request({
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": "antigravity://status"}
    })
    assert "contents" in res_read["result"]
    print("  ✅ 'resources' passed successfully.")

    # 10. Test Prompts
    print("Testing 'prompts/list' and 'prompts/get'...")
    p_list = send_request({"jsonrpc": "2.0", "method": "prompts/list", "params": {}})
    prompt_names = [p["name"] for p in p_list["result"]["prompts"]]
    assert "orchestrate-task" in prompt_names
    
    p_get = send_request({
        "jsonrpc": "2.0",
        "method": "prompts/get",
        "params": {"name": "orchestrate-task", "arguments": {"goal": "Build responsive nav bar"}}
    })
    assert "messages" in p_get["result"]
    print("  ✅ 'prompts' passed successfully.")

    proc.terminate()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! The MCP server is 100% operational.")


if __name__ == "__main__":
    run_tests()
