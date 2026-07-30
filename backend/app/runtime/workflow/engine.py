from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ResourceModel, WorkflowRunModel, WorkflowStepExecutionModel
from app.models.enums import ResourceKind
from app.runtime.agent_runner import AgentRunner
from app.runtime.workflow.definition import normalize_definition, validate_workflow_definition
from app.runtime.workflow.routing import select_next_step
from app.runtime.workflow.template import render_template


class WorkflowEngine:
    def __init__(self, agent_runner: AgentRunner | None = None) -> None:
        self.agent_runner = agent_runner or AgentRunner()

    async def run_workflow(
        self,
        db: Session,
        *,
        workflow: ResourceModel,
        input_data: dict[str, Any],
        user_id: str,
        trigger_type: str = "manual",
    ) -> WorkflowRunModel:
        if workflow.kind != ResourceKind.WORKFLOW.value:
            raise HTTPException(status_code=400, detail="Resource is not a workflow")

        validation = validate_workflow_definition(db, workflow)
        if not validation.ok:
            raise HTTPException(status_code=400, detail={"errors": validation.errors, "warnings": validation.warnings})

        started_at = datetime.utcnow()
        run = WorkflowRunModel(
            workflow_id=workflow.id,
            project_id=workflow.project_id,
            triggered_by=user_id,
            trigger_type=trigger_type or "manual",
            input_data=input_data or {},
            status="running",
            started_at=started_at,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            definition = normalize_definition(workflow.config)
            steps = [dict(item) for item in (definition.get("steps") or [])]
            step_by_id = {str(item["id"]): item for item in steps}
            step_ids = [str(item["id"]) for item in steps]
            context: dict[str, Any] = {
                "input": input_data or {},
                "steps": {},
                "last": {},
                "run": {"id": run.id, "workflow_id": workflow.id},
            }

            if self._definition_uses_graph(steps):
                await self._run_graph_steps(db, workflow, run, steps, context, user_id)
            else:
                await self._run_sequential_steps(db, workflow, run, definition, steps, step_by_id, step_ids, context, user_id)

            output_template = definition.get("output") or {"summary": "{{ last.output }}", "steps": "{{ steps }}"}
            output_data = render_template(output_template, context)
            finished_at = datetime.utcnow()
            run.status = "completed"
            run.output_data = output_data if isinstance(output_data, dict) else {"output": output_data}
            run.completed_at = finished_at
            run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            db.commit()
            db.refresh(run)
            return run
        except Exception as exc:
            finished_at = datetime.utcnow()
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = finished_at
            run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            db.commit()
            db.refresh(run)
            return run

    async def _run_sequential_steps(
        self,
        db: Session,
        workflow: ResourceModel,
        run: WorkflowRunModel,
        definition: dict[str, Any],
        steps: list[dict[str, Any]],
        step_by_id: dict[str, dict[str, Any]],
        step_ids: list[str],
        context: dict[str, Any],
        user_id: str,
    ) -> None:
        current_id = str(definition.get("start_step") or step_ids[0])
        visited: set[str] = set()
        order_index = 0

        while current_id:
            if current_id in visited:
                raise RuntimeError(f"Workflow loop detected at step {current_id}")
            visited.add(current_id)
            step = step_by_id[current_id]
            try:
                output_data = await self._execute_step(db, workflow, run, step, current_id, context, user_id, order_index)
                current_id = select_next_step(step, output_data, step_ids, step_ids.index(current_id))
                order_index += 1
            except Exception as exc:
                on_error = step.get("on_error")
                if on_error:
                    context["last"] = {"id": current_id, "error": str(exc), "output": None}
                    current_id = str(on_error)
                    order_index += 1
                    continue
                raise

    async def _run_graph_steps(
        self,
        db: Session,
        workflow: ResourceModel,
        run: WorkflowRunModel,
        steps: list[dict[str, Any]],
        context: dict[str, Any],
        user_id: str,
    ) -> None:
        step_by_id = {str(item["id"]): item for item in steps}
        completed: set[str] = set()
        order_index = 0

        while len(completed) < len(steps):
            ready_steps = [
                step
                for step in steps
                if str(step["id"]) not in completed
                and all(dependency_id in completed for dependency_id in self._step_dependencies(step, steps))
            ]
            if not ready_steps:
                remaining = [str(step["id"]) for step in steps if str(step["id"]) not in completed]
                raise RuntimeError(f"No runnable workflow steps; check cycles or missing dependencies: {', '.join(remaining)}")

            for step in ready_steps:
                step_id = str(step["id"])
                if step_id not in step_by_id:
                    raise RuntimeError(f"Unknown workflow step: {step_id}")
                await self._execute_step(db, workflow, run, step, step_id, context, user_id, order_index)
                completed.add(step_id)
                order_index += 1

    async def _execute_step(
        self,
        db: Session,
        workflow: ResourceModel,
        run: WorkflowRunModel,
        step: dict[str, Any],
        step_id: str,
        context: dict[str, Any],
        user_id: str,
        order_index: int,
    ) -> Any:
        step_input_value = render_template(step.get("input") or {}, context)
        step_text = self._coerce_step_input_text(step_input_value)
        step_started = datetime.utcnow()
        step_record = WorkflowStepExecutionModel(
            workflow_run_id=run.id,
            step_id=step_id,
            step_name=step.get("name"),
            agent_id=str(step.get("agent_id")),
            input_data=step_input_value if isinstance(step_input_value, dict) else {"text": step_text},
            status="running",
            started_at=step_started,
            order_index=order_index,
        )
        db.add(step_record)
        db.commit()
        db.refresh(step_record)

        try:
            result = await self.agent_runner.run_agent(
                db,
                project_id=workflow.project_id,
                agent_id=str(step.get("agent_id")),
                user_id=user_id,
                input_text=step_text,
                workflow_run_id=run.id,
                extra_context={
                    "workflow_id": workflow.id,
                    "workflow_name": workflow.name,
                    "run_id": run.id,
                    "step_id": step_id,
                    "context": context,
                },
            )
            output_data = self._normalize_agent_output(result.text, step)
            step_record.status = "completed"
            step_record.output_data = {
                "output": output_data,
                "text": result.text,
                "agent_name": result.agent_name,
                "used_tools": result.used_tools,
                "used_mcps": result.used_mcps,
                "used_skills": result.used_skills,
                "used_knowledge_bases": result.used_knowledge_bases,
                "events": result.events,
            }
            completed_at = datetime.utcnow()
            step_record.completed_at = completed_at
            step_record.duration_ms = int((completed_at - step_started).total_seconds() * 1000)
            db.commit()

            context["steps"][step_id] = {
                "id": step_id,
                "name": step.get("name"),
                "input": step_input_value,
                "output": output_data,
                "text": result.text,
            }
            context["last"] = context["steps"][step_id]
            return output_data
        except Exception as exc:
            completed_at = datetime.utcnow()
            step_record.status = "failed"
            step_record.error_message = str(exc)
            step_record.completed_at = completed_at
            step_record.duration_ms = int((completed_at - step_started).total_seconds() * 1000)
            db.commit()
            raise

    @staticmethod
    def _definition_uses_graph(steps: list[dict[str, Any]]) -> bool:
        return any(step.get("next") is not None or step.get("depends_on") is not None for step in steps)

    @staticmethod
    def _step_dependencies(step: dict[str, Any], steps: list[dict[str, Any]]) -> list[str]:
        explicit = _as_string_list(step.get("depends_on"))
        if explicit:
            return explicit
        step_id = str(step["id"])
        dependencies: list[str] = []
        for other in steps:
            other_id = str(other["id"])
            for next_id in _as_string_list(other.get("next")):
                if next_id == step_id and other_id not in dependencies:
                    dependencies.append(other_id)
        return dependencies

    @staticmethod
    def _coerce_step_input_text(step_input: Any) -> str:
        if isinstance(step_input, str):
            return step_input
        if isinstance(step_input, dict):
            text = step_input.get("text") or step_input.get("input") or step_input.get("prompt")
            if text is not None:
                return str(text)
        return _json_dumps(step_input)

    @staticmethod
    def _normalize_agent_output(text: str, step: dict[str, Any]) -> Any:
        output_mode = str(step.get("output_mode") or "text").strip().lower()
        if output_mode == "json":
            try:
                return _extract_json(text)
            except Exception:
                return {"text": text}
        return text


def list_workflow_steps(db: Session, run_id: str) -> list[WorkflowStepExecutionModel]:
    return list(
        db.scalars(
            select(WorkflowStepExecutionModel)
            .where(WorkflowStepExecutionModel.workflow_run_id == run_id)
            .order_by(WorkflowStepExecutionModel.order_index.asc(), WorkflowStepExecutionModel.created_at.asc())
        ).all()
    )


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    item = str(value).strip()
    return [item] if item else []


def _extract_json(text: str) -> Any:
    import json
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    return json.loads(raw)


def _json_dumps(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, indent=2)