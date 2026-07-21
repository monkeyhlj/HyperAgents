"""Integration test for ReAct Agent in Chat API.

This script tests the new ReActAgent integration by sending a message through the Chat API
with engine_type="react" in the agent config.
"""

import requests
import json
import time
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"

# Test user (you should have a valid user ID from your system)
USER_ID = "test-user-001"
PROJECT_ID = "test-project-001"


def create_chat_session(title: str = "Test ReAct Agent Session") -> dict:
    """Create a new chat session."""
    url = f"{BASE_URL}/projects/{PROJECT_ID}/sessions"
    payload = {"title": title}
    
    response = requests.post(
        url,
        json=payload,
        headers={"User-ID": USER_ID},
    )
    print(f"[CREATE SESSION] Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"  Session ID: {result.get('id')}")
        return result
    else:
        print(f"  Error: {response.text}")
        return {}


def list_agents(project_id: str) -> list:
    """List all agents in a project."""
    url = f"{BASE_URL}/projects/{project_id}/agents"
    
    response = requests.get(
        url,
        headers={"User-ID": USER_ID},
    )
    print(f"[LIST AGENTS] Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"  Found {len(result)} agents")
        return result
    else:
        print(f"  Error: {response.text}")
        return []


def get_agent(agent_id: str, project_id: str) -> dict:
    """Get agent details."""
    url = f"{BASE_URL}/projects/{project_id}/agents/{agent_id}"
    
    response = requests.get(
        url,
        headers={"User-ID": USER_ID},
    )
    print(f"[GET AGENT] Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"  Agent: {result.get('name')}")
        print(f"  Config: {json.dumps(result.get('config', {}), indent=2)}")
        return result
    else:
        print(f"  Error: {response.text}")
        return {}


def send_message(
    session_id: str,
    text: str,
    agent_id: Optional[str] = None,
) -> dict:
    """Send a message to the chat."""
    url = f"{BASE_URL}/sessions/{session_id}/messages"
    payload = {
        "text": text,
        "agent_id": agent_id,
    }
    
    print(f"\n[SEND MESSAGE] Text: {text[:100]}...")
    print(f"  Agent: {agent_id}")
    
    response = requests.post(
        url,
        json=payload,
        headers={"User-ID": USER_ID},
    )
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        print(f"  Error: {response.text}")
        return {}


def get_runtime_run_events(run_id: str) -> list:
    """Get events from a runtime run."""
    url = f"{BASE_URL}/runs/{run_id}/events"
    
    response = requests.get(
        url,
        headers={"User-ID": USER_ID},
    )
    print(f"\n[GET RUN EVENTS] Status: {response.status_code}")
    
    if response.status_code == 200:
        events = response.json()
        print(f"  Total events: {len(events)}")
        
        # Group and display by stage
        stages = {}
        for event in events:
            stage = event.get("stage", "unknown")
            if stage not in stages:
                stages[stage] = []
            stages[stage].append(event)
        
        for stage in sorted(stages.keys()):
            print(f"    {stage}: {len(stages[stage])} events")
        
        return events
    else:
        print(f"  Error: {response.text}")
        return []


def main():
    """Main integration test flow."""
    print("=" * 70)
    print("HyperAgents ReAct Agent Integration Test")
    print("=" * 70)
    
    # Step 1: List agents
    print("\n[Step 1] Listing agents...")
    agents = list_agents(PROJECT_ID)
    
    if not agents:
        print("  No agents found. Please create an agent first.")
        return
    
    # Use the first agent as test
    agent_id = agents[0].get("id")
    print(f"  Using agent: {agent_id}")
    
    # Step 2: Get agent details
    print("\n[Step 2] Getting agent details...")
    agent = get_agent(agent_id, PROJECT_ID)
    current_config = agent.get("config", {})
    
    # Check if engine_type is set
    engine_type = current_config.get("engine_type", "legacy")
    print(f"  Current engine_type: {engine_type}")
    
    # Step 3: Create a test session
    print("\n[Step 3] Creating chat session...")
    session = create_chat_session("Test ReAct Agent")
    
    if not session:
        print("  Failed to create session")
        return
    
    session_id = session.get("id")
    
    # Step 4: Send a test message
    print("\n[Step 4] Sending test message...")
    test_message = "What is 2 + 2? Please use the calculator tool."
    response = send_message(session_id, test_message, agent_id)
    
    if not response:
        print("  Failed to send message")
        return
    
    # Get the runtime run ID from response
    run_id = response.get("runtime_run_id")
    if not run_id:
        print("  No runtime_run_id in response")
        print(f"  Response keys: {response.keys()}")
        return
    
    print(f"  Run ID: {run_id}")
    answer = response.get("answer", response.get("text", ""))
    print(f"  Assistant: {answer[:200]}...")
    
    # Step 5: Wait a moment for events to be persisted
    print("\n[Step 5] Waiting for events to be recorded...")
    time.sleep(1)
    
    # Step 6: Get runtime events
    print("\n[Step 6] Retrieving runtime events...")
    events = get_runtime_run_events(run_id)
    
    if events:
        print("\n[Event Details]")
        for i, event in enumerate(events, 1):
            stage = event.get("stage")
            status = event.get("status")
            message = event.get("message", "")
            print(f"  {i}. [{stage}] {status}: {message}")
            
            # Print agentic events details
            if "agentic" in stage:
                payload = event.get("payload", {})
                if payload:
                    print(f"     Content: {str(payload)[:150]}...")
    
    print("\n" + "=" * 70)
    print("Integration test completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
