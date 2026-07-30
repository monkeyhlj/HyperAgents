from __future__ import annotations

from pydantic import BaseModel, Field


class WorkflowRunRequest(BaseModel):
    input_data: dict = Field(default_factory=dict)
    trigger_type: str = Field(default="manual", max_length=30)


class WorkflowDefinitionValidationResult(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WorkflowStepExecutionRecord(BaseModel):
    id: str
    workflow_run_id: str
    step_id: str
    step_name: str | None = None
    agent_id: str
    input_data: dict = Field(default_factory=dict)
    output_data: dict | None = None
    status: str
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    order_index: int
    created_at: str


class WorkflowRunRecord(BaseModel):
    id: str
    workflow_id: str
    project_id: str
    triggered_by: str
    trigger_type: str
    input_data: dict = Field(default_factory=dict)
    status: str
    output_data: dict | None = None
    error_message: str | None = None
    started_at: str
    completed_at: str | None = None
    duration_ms: int | None = None
    created_at: str


class WorkflowRunDetail(WorkflowRunRecord):
    steps: list[WorkflowStepExecutionRecord] = Field(default_factory=list)
