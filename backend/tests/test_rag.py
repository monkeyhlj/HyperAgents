import os, sys, asyncio
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')

from app.db.session import SessionLocal
from app.db.models import DocumentModel, DocumentChunkModel
from app.runtime.knowledge_service import KnowledgeService

async def test():
    db = SessionLocal()
    try:
        docs = db.query(DocumentModel).all()
        for d in docs:
            chunks = db.query(DocumentChunkModel).filter(DocumentChunkModel.document_id == d.id).all()
            print(f"Doc: {d.filename}")
            print(f"  status={d.status}, chunks={len(chunks)}, knowledge_id={d.knowledge_id}")
            if chunks:
                print(f"  Sample: {chunks[0].content[:120]}")
        
        if docs:
            kb_id = docs[0].knowledge_id
            print(f"\nTesting text search on kb_id={kb_id}")
            results = await KnowledgeService.retrieve_from_knowledge(
                db=db,
                knowledge_id=kb_id,
                query_text="个金客户经理准入条件",
                query_embedding=None,
                top_k=3,
            )
            print(f"Results found: {len(results)}")
            for r in results:
                print(f"  File: {r['filename']}")
                print(f"  Content: {r['content'][:200]}")
    finally:
        db.close()

asyncio.run(test())
