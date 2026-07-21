#!/usr/bin/env python3
"""Test MCP weather tool execution via Chat API."""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_mcp_weather():
    """Test weather query via MCP tool."""
    
    print("=" * 80)
    print("MCP Weather Tool Test (testgaode)")
    print("=" * 80)
    
    try:
        # Step 1: Get projects
        print("\n[1] Getting projects...")
        projects_response = requests.get(
            f"{BASE_URL}/projects",
            headers={"Content-Type": "application/json"}
        )
        
        if projects_response.status_code != 200:
            print(f"❌ Failed to get projects: {projects_response.text}")
            return False
            
        projects = projects_response.json()
        if not projects:
            print("❌ No projects available")
            return False
            
        project_id = projects[0]["id"]
        print(f"✅ Using project: {project_id}")
        
        # Step 2: List MCPs in project
        print(f"\n[2] Listing MCPs in project {project_id}...")
        mcps_response = requests.get(
            f"{BASE_URL}/resources/projects/{project_id}?kind=mcp",
            headers={"Content-Type": "application/json"}
        )
        
        mcps = mcps_response.json() if mcps_response.status_code == 200 else []
        print(f"✅ Found {len(mcps)} MCPs in project")
        for mcp in mcps:
            print(f"   - {mcp.get('name')}: {mcp.get('id')}")
        
        # Find testgaode MCP
        testgaode_mcp = None
        for mcp in mcps:
            if 'testgaode' in mcp.get('name', '').lower() or 'weather' in mcp.get('name', '').lower():
                testgaode_mcp = mcp
                break
        
        if not testgaode_mcp:
            print("\n⚠️  testgaode MCP not found in project. Creating it...")
            # Create MCP
            create_mcp_payload = {
                "name": "testgaode",
                "description": "Weather query via Amap API",
                "kind": "mcp",
                "spec": {
                    "transport": "streamable_http",
                    "endpoint_url": "https://mcp.amap.com/sse?key=19685d46b28ebc43f781bbeb5685e74b",
                    "timeout_seconds": 8
                }
            }
            
            create_response = requests.post(
                f"{BASE_URL}/resources/projects/{project_id}",
                json=create_mcp_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if create_response.status_code != 200:
                print(f"❌ Failed to create MCP: {create_response.text}")
                return False
            
            testgaode_mcp = create_response.json()
            print(f"✅ Created MCP: {testgaode_mcp.get('id')}")
        else:
            print(f"✅ Found testgaode MCP: {testgaode_mcp.get('id')}")
        
        mcp_id = testgaode_mcp.get('id')
        
        # Step 3: Get agents
        print("\n[3] Getting agents...")
        agents_response = requests.get(
            f"{BASE_URL}/resources/projects/{project_id}?kind=agent",
            headers={"Content-Type": "application/json"}
        )
        
        agents = agents_response.json() if agents_response.status_code == 200 else []
        
        if not agents:
            print("❌ No agents found in project")
            return False
        
        # Prefer Zhipu agent
        agent = None
        for a in agents:
            if a.get('model_provider') == 'zhipu':
                agent = a
                break
        
        if not agent:
            agent = agents[0]
        
        agent_id = agent.get('id')
        print(f"✅ Using agent: {agent_id} ({agent.get('name')})")
        
        # Step 4: Create chat session
        print("\n[4] Creating chat session...")
        session_payload = {"title": "MCP Weather Test"}
        session_response = requests.post(
            f"{BASE_URL}/chat/projects/{project_id}/sessions",
            json=session_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if session_response.status_code != 200:
            print(f"❌ Failed to create session: {session_response.text}")
            return False
        
        session = session_response.json()
        session_id = session.get('id')
        print(f"✅ Created session: {session_id}")
        
        # Step 5: Send message with ReAct + MCP
        print("\n[5] Sending message: '今天成都的天气怎么样'")
        print(f"   Session ID: {session_id}")
        print(f"   Agent ID: {agent_id}")
        print(f"   MCP ID: {mcp_id}")
        print(f"   Project ID: {project_id}")
        message_payload = {
            "text": "今天成都的天气怎么样",
            "agent_id": agent_id,
            "engine_type": "react",
            "provider_profile": "zhipu",
            "temperature": 0.2,
            "max_iterations": 5,
            "mcp_ids": [mcp_id]  # ✅ Key: use MCP
        }
        
        message_response = requests.post(
            f"{BASE_URL}/chat/sessions/{session_id}/messages",
            json=message_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if message_response.status_code != 200:
            print(f"❌ Failed to send message: {message_response.status_code}")
            print(f"   Response: {message_response.text}")
            return False
        
        message = message_response.json()
        run_id = message.get('run_id')
        answer = message.get('answer')
        
        print(f"✅ Got response from agent")
        print(f"   Run ID: {run_id}")
        print(f"   Answer: {answer[:200]}..." if len(answer) > 200 else f"   Answer: {answer}")
        
        # Step 6: Get full event timeline
        print(f"\n[6] Fetching event timeline for run {run_id}...")
        time.sleep(0.5)  # Small delay
        
        events_response = requests.get(
            f"{BASE_URL}/chat/runs/{run_id}/events",
            headers={"Content-Type": "application/json"}
        )
        
        events = events_response.json() if events_response.status_code == 200 else []
        
        print(f"✅ Retrieved {len(events)} events")
        print("\n   Event Timeline:")
        
        for i, event in enumerate(events, 1):
            stage = event.get('stage', 'unknown')
            status = event.get('status', 'unknown')
            payload = event.get('payload', {})
            
            print(f"   [{i}] {stage:20} | {status:10}", end="")
            
            # Show payload details
            if stage.startswith('agentic_'):
                if 'tool_name' in payload:
                    print(f" | Tool: {payload['tool_name']}", end="")
                    if payload.get('tool_result'):
                        result_preview = str(payload['tool_result'])[:100]
                        print(f" | Result: {result_preview}...", end="")
                elif 'content' in payload:
                    content_preview = str(payload['content'])[:100]
                    print(f" | Content: {content_preview}...", end="")
            
            print()
        
        # Step 7: Check for tool execution
        print("\n[7] Analysis:")
        has_tool_call = any('tool_name' in e.get('payload', {}) for e in events)
        has_observation = any(e.get('stage') == 'agentic_observation' for e in events)
        
        if has_tool_call:
            print("   ✅ Tool was called by agent")
        else:
            print("   ❌ No tool calls found in events")
        
        if has_observation:
            print("   ✅ Tool execution recorded")
        else:
            print("   ❌ No observation events found")
        
        return True
        
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mcp_weather()
    sys.exit(0 if success else 1)
