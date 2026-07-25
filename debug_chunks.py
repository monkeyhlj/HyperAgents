import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')

from app.db.session import SessionLocal
from app.db.models import DocumentChunkModel, DocumentModel
from sqlalchemy import select

db = SessionLocal()

# Print all chunks
kb_id = '1db89726-cb34-4759-97fc-c5ca97d33082'
chunks = db.execute(
    select(DocumentChunkModel).join(DocumentModel).where(
        DocumentChunkModel.knowledge_id == kb_id,
        DocumentModel.status == 'ready'
    )
).scalars().all()

print(f"Total chunks: {len(chunks)}")
for c in chunks:
    print(f"\n--- Chunk {c.chunk_index} (embedding_status={c.embedding_status}) ---")
    print(c.content[:300])

db.close()
