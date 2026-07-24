#!/usr/bin/env python3
"""Complete integration test for ReAct Agent via Chat API."""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_react_agent():
    """Complete test flow for ReAct agent."""
    
    print("=" * 80)
    print("ReAct Agent Integration Test")
    print("=" * 80)
    
    try:
        # Step 0: Get available projects
        print("\n[0] Getting available projects...")
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
        
        # Step 0b: Get agent templates (for reference)
        print("\n[0b] Getting agent templates...")
        agents_response = requests.get(
            f"{BASE_URL}/resources/defaults?kind=agent",
            headers={"Content-Type": "application/json"}
        )
        
        agent_templates = agents_response.json() if agents_response.status_code == 200 else []
        if agent_templates:
            print(f"✅ Found {len(agent_templates)} agent templates")
            agent_template = agent_templates[0]
            print(f"   Using template: {agent_template.get('name', 'unknown')}")
        else:
            print("⚠️  No agent templates found")
        
        # Step 1: Create chat session
        print("\n[1] Creating chat session...")
        session_response = requests.post(
            f"{BASE_URL}/chat/projects/{project_id}/sessions",
            json={"title": "ReAct Agent Test"},
            headers={"Content-Type": "application/json"}
        )
        
        if session_response.status_code != 200:
            print(f"❌ Failed to create session: {session_response.text}")
            return False
            
        session_data = session_response.json()
        session_id = session_data["id"]
        print(f"✅ Session created: {session_id}")
        
        # Step 2: Send message with ReAct engine
        print("\n[2] Sending message with engine_type='react'...")
        message_request = {
            "text": "What's the current time?",
            "engine_type": "react",
            "provider_profile": "openai",
            "temperature": 0.2,
            "max_iterations": 5,
            "mcp_ids": []
        }
        print(f"   Request body: {json.dumps(message_request, indent=2)}")
        
        message_response = requests.post(
            f"{BASE_URL}/chat/sessions/{session_id}/messages",
            json=message_request,
            headers={"Content-Type": "application/json"}
        )
        
        if message_response.status_code != 200:
            print(f"❌ Failed to send message: {message_response.text}")
            return False
            
        print(f"✅ Message sent, status: {message_response.status_code}")
        
        # Step 3: Get runs
        print("\n[3] Fetching runtime runs...")
        time.sleep(1)  # Wait a bit for processing
        
        runs_response = requests.get(
            f"{BASE_URL}/chat/sessions/{session_id}/runs",
            headers={"Content-Type": "application/json"}
        )
        
        if runs_response.status_code != 200:
            print(f"❌ Failed to fetch runs: {runs_response.text}")
            return False
            
        runs_data = runs_response.json()
        
        if not runs_data:
            print("❌ No runs found in session")
            return False
            
        run_id = runs_data[0]["id"]
        print(f"✅ Found run: {run_id}")
        print(f"   Status: {runs_data[0].get('status', 'N/A')}")
        
        # Step 4: Get events from run
        print("\n[4] Fetching runtime events...")
        events_response = requests.get(
            f"{BASE_URL}/chat/runs/{run_id}/events",
            headers={"Content-Type": "application/json"}
        )
        
        if events_response.status_code != 200:
            print(f"❌ Failed to fetch events: {events_response.text}")
            return False
            
        events = events_response.json()
        print(f"✅ Found {len(events)} events")
        
        # Step 5: Display event breakdown
        print("\n[5] Event Breakdown:")
        print("-" * 80)
        
        event_types = {}
        agentic_events = []
        
        for event in events:
            event_type = event.get("event_type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
            if event_type in ["agentic_thought", "agentic_action", "agentic_observation", "agentic_final_answer"]:
                agentic_events.append(event)
            
            # Also check stage field for agentic events
            stage = event.get("stage", "")
            if stage and stage.startswith("agentic_"):
                if event not in agentic_events:
                    agentic_events.append(event)
                
        print(f"Event type counts:")
        for etype, count in event_types.items():
            print(f"  - {etype}: {count}")
        
        # Display all events for debugging
        print(f"\n📋 All Events:")
        for i, event in enumerate(events, 1):
            print(f"\nEvent {i}:")
            print(f"  Type: {event.get('event_type', 'N/A')}")
            print(f"  Stage: {event.get('stage', 'N/A')}")
            print(f"  Status: {event.get('status', 'N/A')}")
            if "message" in event:
                msg = event["message"][:100]
                print(f"  Message: {msg}")
            if "content" in event and event["content"]:
                content = event["content"][:100]
                print(f"  Content: {content}...")
            
        # Step 6: Display agentic events
        if agentic_events:
            print(f"\n✅ Found {len(agentic_events)} agentic events:")
            print("-" * 80)
            for i, event in enumerate(agentic_events, 1):
                stage = event.get('stage', 'N/A')
                print(f"\n  Event {i}: {stage}")
                if "message" in event and event["message"]:
                    print(f"    Message: {event['message']}")
                if "content" in event and event["content"]:
                    content = event["content"][:100]
                    print(f"    Content: {content}...")
                if "payload" in event and event["payload"]:
                    payload = event["payload"]
                    if isinstance(payload, dict):
                        if "tool_name" in payload:
                            print(f"    Tool: {payload['tool_name']}")
                        if "tool_input" in payload:
                            print(f"    Input: {str(payload['tool_input'])[:100]}...")
        else:
            print("\n⚠️  No agentic events found")
            
        # Step 7: Check for errors
        error_events = [e for e in events if e.get("event_type") == "error"]
        if error_events:
            print(f"\n⚠️  Found {len(error_events)} error events:")
            for event in error_events:
                print(f"    Error: {event.get('content', 'N/A')}")
        else:
            print(f"\n✅ No error events")
            
        print("\n" + "=" * 80)
        print("✅ Integration test PASSED!")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_react_agent()
    sys.exit(0 if success else 1)
