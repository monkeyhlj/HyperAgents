import os, sys, asyncio, urllib.request, json
sys.path.insert(0, 'backend')

import os
os.environ['PYTHONPATH'] = 'backend'

# Direct API test
BASE_URL = "http://127.0.0.1:8000"

def api_post(url, data, headers=None):
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers=req_headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())

def api_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

# 1. Login with the project owner
login_resp = api_post(f"{BASE_URL}/api/v1/auth/login", {"account": "hljtest2", "password": "Test123!"})
token = login_resp["access_token"]
print(f"Token: {token[:20]}...")

auth_headers = {"Authorization": f"Bearer {token}"}

# 2. Get sessions for the project
sessions_resp = api_get(f"{BASE_URL}/api/v1/chat/projects/0cbb5b5d-7e4b-4772-81b5-113f06d88882/sessions", auth_headers)
session_id = sessions_resp[0]["id"]
print(f"Session: {session_id}")

# 3. Send message
msg_headers = {**auth_headers, "Content-Type": "application/json"}
req = urllib.request.Request(
    f"{BASE_URL}/api/v1/chat/sessions/{session_id}/messages",
    data=json.dumps({
        "text": "上海浦东发展银行西安分行 个金客户经理准入条件是什么",
        "agent_id": "7e1aaff1-65b3-4d5d-b20c-f041f5eb982f"
    }).encode(),
    headers=msg_headers,
    method="POST"
)
with urllib.request.urlopen(req, timeout=90) as resp:
    response = json.loads(resp.read())

print(f"\nUsed Knowledge Bases: {response.get('used_knowledge_bases', [])}")
print(f"\nResponse:\n{response['text'][:1000]}")
