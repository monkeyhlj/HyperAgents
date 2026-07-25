import os, sys, asyncio
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')

from app.db.session import SessionLocal
from app.db.models import ResourceModel, ChatSessionModel
from app.runtime.knowledge_service import KnowledgeService
from sqlalchemy import select

async def test():
    db = SessionLocal()
    try:
        # Find the agent with KB
        agent = db.execute(select(ResourceModel).where(
            ResourceModel.id == '7e1aaff1-65b3-4d5d-b20c-f041f5eb982f'
        )).scalar_one_or_none()
        
        print(f"Agent: {agent.name}")
        print(f"Config: {agent.config}")
        
        kb_ids = agent.config.get('knowledge_base_ids', [])
        print(f"KB IDs: {kb_ids}")
        
        # Test RAG retrieval
        query = "个金客户经理准入条件是什么"
        print(f"\nQuery: {query}")
        
        # Try without embedding (full text search)
        context = await KnowledgeService.build_rag_context(
            db=db,
            agent_id=agent.id,
            query_text=query,
            query_embedding=None,
            knowledge_base_ids=kb_ids,
        )
        
        print(f"\nRAG context length: {len(context)}")
        print(f"\nRAG context:\n{context[:1000]}")
    finally:
        db.close()

asyncio.run(test())
