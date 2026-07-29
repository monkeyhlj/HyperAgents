from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.db.models import ResourceModel, WorkflowRunModel
from app.db.schema import ensure_workflow_tables
from app.models.enums import ResourceKind
from app.runtime.workflow.definition import validate_workflow_definition
from app.runtime.workflow.engine import WorkflowEngine, list_workflow_steps
from app.schemas.workflow import (
    WorkflowDefinitionValidationResult,
    WorkflowRunDetail,
    WorkflowRunRecord,
    WorkflowRunRequest,
    WorkflowStepExecutionRecord,
)
from app.services.postgres_store import store

router = APIRouter(tags=["workflows"])


def _ensure_runtime_tables() -> None:
    ensure_workflow_tables()


@router.post("/{workflow_id}/validate", response_model=WorkflowDefinitionValidationResult)
def validate_workflow(
    workflow_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> WorkflowDefinitionValidationResult:
    workflow = _get_workflow_model(db, workflow_id, user_id)
    result = validate_workflow_definition(db, workflow)
    return WorkflowDefinitionValidationResult(ok=result.ok, errors=result.errors, warnings=result.warnings)


@router.post("/{workflow_id}/run", response_model=WorkflowRunDetail)
async def run_workflow(
    workflow_id: str,
    payload: WorkflowRunRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> WorkflowRunDetail:
    _ensure_runtime_tables()
    workflow = _get_workflow_model(db, workflow_id, user_id)
    run = await WorkflowEngine().run_workflow(
        db,
        workflow=workflow,
        input_data=payload.input_data or {},
        user_id=user_id,
        trigger_type=payload.trigger_type or "manual",
    )
    return _to_run_detail(db, run)


@router.get("/{workflow_id}/runs", response_model=list[WorkflowRunRecord])
def list_workflow_runs(
    workflow_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[WorkflowRunRecord]:
    _ensure_runtime_tables()
    workflow = _get_workflow_model(db, workflow_id, user_id)
    runs = db.scalars(
        select(WorkflowRunModel)
        .where(WorkflowRunModel.workflow_id == workflow.id)
        .order_by(WorkflowRunModel.created_at.desc())
        .limit(limit)
    ).all()
    return [_to_run_record(item) for item in runs]


@router.get("/{workflow_id}/runs/{run_id}", response_model=WorkflowRunDetail)
def get_workflow_run(
    workflow_id: str,
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> WorkflowRunDetail:
    _ensure_runtime_tables()
    workflow = _get_workflow_model(db, workflow_id, user_id)
    run = db.get(WorkflowRunModel, run_id)
    if not run or run.workflow_id != workflow.id:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return _to_run_detail(db, run)


def _get_workflow_model(db: Session, workflow_id: str, user_id: str) -> ResourceModel:
    workflow = db.get(ResourceModel, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    store.assert_project_member(db, workflow.project_id, user_id)
    if workflow.kind != ResourceKind.WORKFLOW.value:
        raise HTTPException(status_code=400, detail="Resource is not a workflow")
    return workflow


def _to_run_detail(db: Session, run: WorkflowRunModel) -> WorkflowRunDetail:
    return WorkflowRunDetail(**_to_run_record(run).model_dump(), steps=[_to_step_record(item) for item in list_workflow_steps(db, run.id)])


def _to_run_record(run: WorkflowRunModel) -> WorkflowRunRecord:
    return WorkflowRunRecord(
        id=run.id,
        workflow_id=run.workflow_id,
        project_id=run.project_id,
        triggered_by=run.triggered_by,
        trigger_type=run.trigger_type,
        input_data=run.input_data or {},
        status=run.status,
        output_data=run.output_data,
        error_message=run.error_message,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        duration_ms=run.duration_ms,
        created_at=run.created_at.isoformat(),
    )


def _to_step_record(step) -> WorkflowStepExecutionRecord:
    return WorkflowStepExecutionRecord(
        id=step.id,
        workflow_run_id=step.workflow_run_id,
        step_id=step.step_id,
        step_name=step.step_name,
        agent_id=step.agent_id,
        input_data=step.input_data or {},
        output_data=step.output_data,
        status=step.status,
        error_message=step.error_message,
        started_at=step.started_at.isoformat() if step.started_at else None,
        completed_at=step.completed_at.isoformat() if step.completed_at else None,
        duration_ms=step.duration_ms,
        order_index=step.order_index,
        created_at=step.created_at.isoformat(),
    )
