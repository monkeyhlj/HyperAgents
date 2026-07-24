#!/usr/bin/env python3
"""Debug agent structure."""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Get projects
projects_response = requests.get(f"{BASE_URL}/projects", headers={"Content-Type": "application/json"})
projects = projects_response.json()
project_id = projects[0]["id"]

# Get agents
agents_response = requests.get(
    f"{BASE_URL}/resources/defaults?kind=agent",
    headers={"Content-Type": "application/json"}
)

print("=" * 80)
print("Agent Structure Debug")
print("=" * 80)
print(f"\nProject ID: {project_id}")
print(f"\nAgents response status: {agents_response.status_code}")
print(f"\nAgents response (first item):")
agents = agents_response.json()
if agents:
    print(json.dumps(agents[0], indent=2))
else:
    print("No agents found")
