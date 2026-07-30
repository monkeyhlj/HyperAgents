from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
import logging
import asyncio
import time
import sys
import os

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.db.schema import ensure_workflow_tables
import app.db.models  # noqa: F401
from app.workers.knowledge_processor import process_pending_documents, process_pending_embeddings

def _resolve_log_level(value: str, default: int = logging.INFO) -> int:
    return getattr(logging, (value or "INFO").upper(), default)


app_log_level = _resolve_log_level(settings.log_level)
uvicorn_log_level = _resolve_log_level(settings.uvicorn_log_level, app_log_level)

# Configure logging with explicit StreamHandler to stdout.
logging.basicConfig(
    level=app_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

logging.getLogger("app").setLevel(app_log_level)
logging.getLogger("uvicorn").setLevel(uvicorn_log_level)
logging.getLogger("uvicorn.access").setLevel(uvicorn_log_level)
logging.getLogger("uvicorn.error").setLevel(uvicorn_log_level)

logger = logging.getLogger(__name__)
logger.setLevel(app_log_level)
app = FastAPI(title=settings.app_name, version=settings.app_version)
logger.info(f"App process started: pid={os.getpid()}, ppid={os.getppid() if hasattr(os, 'getppid') else '-'}, cwd={os.getcwd()}")

# Background task scheduler
background_task_handle = None


@app.on_event("startup")
def on_startup() -> None:
    logger.info(f"Application startup hook running: pid={os.getpid()}, cwd={os.getcwd()}")
    if settings.auto_create_tables:
        try:
            Base.metadata.create_all(bind=engine)
        except SQLAlchemyError as exc:
            # Allow local development to start even when DB is temporarily unavailable.
            print(f"[startup] database initialization skipped: {exc}")
    try:
        ensure_workflow_tables()
    except SQLAlchemyError as exc:
        print(f"[startup] workflow table initialization skipped: {exc}")

    # Start background tasks
    global background_task_handle
    background_task_handle = asyncio.create_task(run_background_tasks())

@app.on_event("shutdown")
def on_shutdown() -> None:
    """Cancel background tasks on shutdown."""
    global background_task_handle
    if background_task_handle:
        background_task_handle.cancel()


async def run_background_tasks():
    """Run periodic background tasks."""
    logger.info("[Background Tasks] Starting background task scheduler")
    
    while True:
        try:
            # Process pending documents every 10 seconds
            await asyncio.sleep(10)
            logger.debug("[Background Tasks] Running process_pending_documents")
            await process_pending_documents()
            
            # Process pending embeddings every 30 seconds
            await asyncio.sleep(20)
            logger.debug("[Background Tasks] Running process_pending_embeddings")
            await process_pending_embeddings()
        
        except asyncio.CancelledError:
            logger.info("[Background Tasks] Background task scheduler cancelled")
            break
        except Exception as e:
            logger.error(f"[Background Tasks] Error in background task: {str(e)}", exc_info=True)
            await asyncio.sleep(5)  # Wait before retrying


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"CORS enabled for origins: {settings.cors_allow_origins}")


def _console_log(message: str) -> None:
    logger.info(message)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every incoming HTTP request to the uvicorn console."""
    if not settings.http_request_logging:
        return await call_next(request)
    start_time = time.perf_counter()
    query = f"?{request.url.query}" if request.url.query else ""
    path = f"{request.url.path}{query}"
    client = request.client.host if request.client else "unknown"
    content_length = request.headers.get("content-length", "-")
    _console_log(f"[HTTP] --> {request.method} {path} client={client} bytes={content_length}")

    try:
        response = await call_next(request)
    except Exception as exc:
        process_time = time.perf_counter() - start_time
        _console_log(f"[HTTP] !!  {request.method} {path} error={type(exc).__name__}: {exc} time={process_time:.3f}s")
        raise

    process_time = time.perf_counter() - start_time
    _console_log(f"[HTTP] <-- {request.method} {path} status={response.status_code} time={process_time:.3f}s")
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/test-cors")
def test_cors() -> dict[str, str]:
    return {"message": "CORS is working"}

@app.post("/test-cors-post")
def test_cors_post() -> dict[str, str]:
    return {"message": "CORS POST is working"}


app.include_router(api_router, prefix="/api")
