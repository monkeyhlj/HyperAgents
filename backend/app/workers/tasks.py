from app.db.session import SessionLocal
from app.services.memory_store import memory_store


def process_embedding_retry(limit: int = 20) -> dict[str, int]:
    with SessionLocal() as session:
        return memory_store.process_pending_embedding_jobs(session, limit=limit)
