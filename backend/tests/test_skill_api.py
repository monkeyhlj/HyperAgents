#!/usr/bin/env python
import sys
sys.path.insert(0, './backend')

from app.services.auth_utils import create_access_token
import requests
import json

# Generate token - create_access_token expects user_id as string
token, expires_in = create_access_token("hljtest2")

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
    if response.status_code != 200:
        print(f"\nError Response: {response.json() if response.text else 'No body'}")
except Exception as e:
    print(f"Error: {e}")
