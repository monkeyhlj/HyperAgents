import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')

from app.db.session import SessionLocal
from app.db.models import ResourceModel, ChatSessionModel
from sqlalchemy import select

db = SessionLocal()

# Find testk1 KB
kb = db.execute(select(ResourceModel).where(
    ResourceModel.kind == 'knowledge_base',
    ResourceModel.name == 'testk1'
)).scalar_one_or_none()

if not kb:
    print("testk1 KB not found!")
    db.close()
    exit(1)

print(f"testk1 KB: id={kb.id}, project={kb.project_id}")

agents = db.execute(select(ResourceModel).where(
    ResourceModel.kind == 'agent',
    ResourceModel.project_id == kb.project_id
)).scalars().all()

print(f"\nAgents in same project ({kb.project_id}):")
for a in agents:
    kb_ids = a.config.get('knowledge_base_ids', []) if a.config else []
    print(f"  {a.name} id={a.id} kb_ids={kb_ids}")

sessions = db.execute(select(ChatSessionModel).where(
    ChatSessionModel.project_id == kb.project_id
)).scalars().all()
print(f"\nChat sessions in this project: {len(sessions)}")
for s in sessions[:3]:
    print(f"  session={s.id}")

db.close()
