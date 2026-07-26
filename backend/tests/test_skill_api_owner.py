#!/usr/bin/env python
import sys
sys.path.insert(0, './backend')

from app.services.auth_utils import create_access_token
import requests

# Use the skill owner's user ID
owner_id = "3f220880-8f0e-482b-aaf7-aef06b614cf1"

# Generate token
token, expires_in = create_access_token(owner_id)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

# Test the skills API endpoint
url = "http://localhost:8000/api/v1/skills/5c674e39-2a1e-42d0-9fa6-35146c4df709"
try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\n✓ SUCCESS! API returned 200")
    else:
        print(f"\nError: {response.text}")
except Exception as e:
    print(f"Error: {e}")
