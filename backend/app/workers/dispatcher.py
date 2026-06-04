from dataclasses import dataclass

from app.core.config import settings


@dataclass
class WorkerDispatchResult:
    queued: bool
    task_id: str | None = None
    reason: str | None = None


def enqueue_embedding_retry(limit: int) -> WorkerDispatchResult:
    if not settings.worker_enabled:
        return WorkerDispatchResult(queued=False, reason="worker_disabled")

    try:
        from celery import Celery

        celery_app = Celery(
            "hyperagents_worker",
            broker=settings.worker_broker_url,
            backend=settings.worker_backend_url,
        )
        task = celery_app.send_task("hyperagents.tasks.process_embedding_retry", kwargs={"limit": limit})
        return WorkerDispatchResult(queued=True, task_id=task.id)
    except Exception as exc:
        return WorkerDispatchResult(queued=False, reason=str(exc))
