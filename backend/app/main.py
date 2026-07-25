from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
import logging
import asyncio

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
import app.db.models  # noqa: F401
from app.workers.knowledge_processor import process_pending_documents, process_pending_embeddings

# Configure logging to show all INFO and DEBUG level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to INFO level
logging.getLogger("app").setLevel(logging.INFO)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version=settings.app_version)

# Background task scheduler
background_task_handle = None


@app.on_event("startup")
def on_startup() -> None:
    if not settings.auto_create_tables:
        return
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as exc:
        # Allow local development to start even when DB is temporarily unavailable.
        print(f"[startup] database initialization skipped: {exc}")
    
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
