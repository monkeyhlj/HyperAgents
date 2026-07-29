from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from app.db.models import WorkflowRunModel, WorkflowStepExecutionModel
from app.db.session import engine


def ensure_workflow_tables() -> None:
    """Create workflow runtime tables when the app is running without Alembic migration."""
    try:
        WorkflowRunModel.__table__.create(bind=engine, checkfirst=True)
        WorkflowStepExecutionModel.__table__.create(bind=engine, checkfirst=True)
    except SQLAlchemyError:
        raise