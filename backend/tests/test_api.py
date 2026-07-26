#!/usr/bin/env python
import sys
sys.path.insert(0, './backend')
from app.services.auth_utils import create_access_token

# Create a token for hljtest2
result = create_access_token("hljtest2")
# result is a tuple (token, expires_in)
if isinstance(result, tuple):
    token = result[0]
else:
    token = result
print(f"Token: {token}")
