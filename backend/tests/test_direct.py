import requests
import json

BASE_URL = 'http://localhost:8000/api/v1'

# Get project
projects = requests.get(f'{BASE_URL}/projects').json()
project_id = projects[0]['id']
print(f'Project ID: {project_id}')

# Create custom Zhipu agent
print('\nCreating custom Zhipu agent...')
agent_resp = requests.post(
    f'{BASE_URL}/resources/projects/{project_id}',
    json={
        'name': 'Test Zhipu Agent',
        'description': 'Test agent for MCP weather',
        'kind': 'agent',
        'visibility': 'project',
        'model_provider': 'zhipu',
        'model_name': 'glm-5.1',
        'provider_profile': 'zhipu',
        'config': {}
    }
)

if agent_resp.status_code != 200:
    print(f'Failed to create agent: {agent_resp.text}')
else:
    agent = agent_resp.json()
    agent_id = agent['id']
    print(f'Created agent: {agent_id}')

# Create session
session_resp = requests.post(
    f'{BASE_URL}/chat/projects/{project_id}/sessions',
    json={'title': 'Test'}
)
print(f'Session creation: {session_resp.status_code}')

if session_resp.status_code == 200:
    session = session_resp.json()
    session_id = session.get('id')
    print(f'Session ID: {session_id}')
    
    # Try POST message without MCP
    message_resp = requests.post(
        f'{BASE_URL}/chat/sessions/{session_id}/messages',
        json={
            'text': 'hello',
            'agent_id': agent_id
        }
    )
    
    print(f'POST message (no MCP) status: {message_resp.status_code}')
    if message_resp.status_code == 200:
        result = message_resp.json()
        print(f'Response: {result.get("text")[:200]}')
    
    # Now test with MCP
    # First get/create MCP
    print('\n---Now testing with MCP---')
    mcps = requests.get(f'{BASE_URL}/resources/projects/{project_id}?kind=mcp').json()
    
    # For now, always create a new one with correct config
    mcp_id = None
    
    if mcps:
        # Delete old MCP (optional, just use new one)
        print(f'Found {len(mcps)} existing MCPs, creating new one with correct transport...')
    
    print('Creating testgaode MCP with SSE transport...')
    mcp_resp = requests.post(
        f'{BASE_URL}/resources/projects/{project_id}',
        json={
            'name': f'testgaode-sse-{int(__import__("time").time())}',
            'description': 'Weather via Amap API (SSE)',
            'kind': 'mcp',
            'visibility': 'project',
            'config': {
                'transport': 'sse',
                'endpoint_url': 'https://mcp.amap.com/sse?key=19685d46b28ebc43f781bbeb5685e74b',
                'timeout_seconds': 8
            }
        }
    )
    if mcp_resp.status_code == 200:
        mcp = mcp_resp.json()
        mcp_id = mcp['id']
        print(f'Created MCP: {mcp_id}')
    else:
        print(f'Failed to create MCP: {mcp_resp.text}')
    
    if not mcp_id and mcps:
        mcp_id = mcps[0]['id']
        print(f'Using existing MCP: {mcp_id}')
    
    if mcp_id:
        # Create new session for MCP test
        session_resp2 = requests.post(
            f'{BASE_URL}/chat/projects/{project_id}/sessions',
            json={'title': 'Weather Test'}
        )
        session_id2 = session_resp2.json()['id']
        
        # Test weather query with MCP + ReAct
        print(f'\nSending weather query...')
        weather_resp = requests.post(
            f'{BASE_URL}/chat/sessions/{session_id2}/messages',
            json={
                'text': '今天成都的天气怎么样',
                'agent_id': agent_id,
                'engine_type': 'react',
                'provider_profile': 'zhipu',
                'mcp_ids': [mcp_id]
            }
        )
        
        print(f'POST weather status: {weather_resp.status_code}')
        if weather_resp.status_code == 200:
            result = weather_resp.json()
            response_text = result.get("text", "")
            print(f'Response: {response_text[:500]}')
            if len(response_text) > 500:
                print(f'...{response_text[-200:]}')
            print(f'Used MCPs: {result.get("used_mcps")}')
            
            # Get events to see tool calls
            run_id = result.get('run_id')
            import time
            time.sleep(0.5)
            
            events_resp = requests.get(f'{BASE_URL}/chat/runs/{run_id}/events')
            events = events_resp.json() if events_resp.status_code == 200 else []
            
            print(f'\nAgent events ({len(events)} total):')
            for i, event in enumerate(events):
                stage = event.get('stage', '?')
                payload = event.get('payload', {})
                print(f'\n  Event {i}: {stage}')
                if isinstance(payload, dict):
                    for key, value in payload.items():
                        if isinstance(value, str) and len(str(value)) > 100:
                            print(f'    {key}: {str(value)[:100]}...')
                        else:
                            print(f'    {key}: {value}')
        else:
            print(f'Error: {weather_resp.text}')
else:
    print(f'Session creation failed: {session_resp.status_code}')
