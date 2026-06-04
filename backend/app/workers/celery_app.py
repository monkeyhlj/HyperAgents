from celery import Celery

from app.core.config import settings
from app.workers.tasks import process_embedding_retry


celery_app = Celery(
    "hyperagents_worker",
    broker=settings.worker_broker_url,
    backend=settings.worker_backend_url,
)


@celery_app.task(name="hyperagents.tasks.process_embedding_retry")
def process_embedding_retry_task(limit: int = 20) -> dict[str, int]:
    return process_embedding_retry(limit=limit)
