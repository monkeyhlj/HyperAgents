#!/usr/bin/env python
import sys
sys.path.insert(0, './backend')

try:
    from app.api.v1 import skills
    print("✓ Skills module imported successfully")
    
    # Check if router is correctly defined
    if hasattr(skills, 'router'):
        print("✓ Router found in skills module")
        print(f"✓ Router has {len(skills.router.routes)} routes")
    else:
        print("✗ Router not found in skills module")
except Exception as e:
    print(f"✗ Error importing skills: {e}")
    import traceback
    traceback.print_exc()
