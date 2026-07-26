#!/usr/bin/env python
import sys
import asyncio
sys.path.insert(0, './backend')

from app.db.session import SessionLocal
from app.api.v1.skills import get_skill_detail

# Run async function
async def test():
    db = SessionLocal()
    try:
        result = await get_skill_detail(
            skill_id="5c674e39-2a1e-42d0-9fa6-35146c4df709",
            user_id="3f220880-8f0e-482b-aaf7-aef06b614cf1",
            db=db
        )
        print("✓ Success!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

# Run the async function
asyncio.run(test())
