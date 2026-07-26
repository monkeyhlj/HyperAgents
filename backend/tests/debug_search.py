import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')

from app.db.session import SessionLocal
from app.db.models import DocumentChunkModel, DocumentModel
from sqlalchemy import select

db = SessionLocal()
kb_id = '1db89726-cb34-4759-97fc-c5ca97d33082'

# Search for "准入" in any chunk
keywords = ["准入", "条件", "学历", "经验", "银行工作", "第七条"]
for kw in keywords:
    results = db.execute(
        select(DocumentChunkModel).join(DocumentModel).where(
            DocumentChunkModel.knowledge_id == kb_id,
            DocumentModel.status == 'ready',
            DocumentChunkModel.content.contains(kw)
        )
    ).scalars().all()
    print(f"Keyword '{kw}': {len(results)} chunks found")
    for r in results:
        idx = r.content.find(kw)
        print(f"  Chunk {r.chunk_index}: ...{r.content[max(0,idx-20):idx+80]}...")

db.close()
