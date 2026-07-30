from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ResourceModel
from app.models.enums import ResourceKind


_STEP_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,120}$")
_TEMPLATE_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_definition(config: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(config or {})
    if "definition" in data and isinstance(data["definition"], dict):
        data = dict(data["definition"])
    return data


def validate_workflow_definition(db: Session, workflow: ResourceModel) -> ValidationResult:
    definition = normalize_definition(workflow.config)
    errors: list[str] = []
    warnings: list[str] = []

    if workflow.kind != ResourceKind.WORKFLOW.value:
        errors.append("Resource is not a workflow")
        return ValidationResult(ok=False, errors=errors, warnings=warnings)

    steps = definition.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("definition.steps must be a non-empty array")
        return ValidationResult(ok=False, errors=errors, warnings=warnings)

    ids: list[str] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"steps[{index}] must be an object")
            continue
        step_id = str(step.get("id") or "").strip()
        if not step_id:
            errors.append(f"steps[{index}].id is required")
        elif not _STEP_ID_RE.match(step_id):
            errors.append(f"steps[{index}].id must use letters, numbers, '_' or '-'")
        else:
            ids.append(step_id)
        agent_id = str(step.get("agent_id") or "").strip()
        if not agent_id:
            errors.append(f"steps[{index}].agent_id is required")
        else:
            agent = db.get(ResourceModel, agent_id)
            if not agent or agent.kind != ResourceKind.AGENT.value or agent.project_id != workflow.project_id:
                errors.append(f"steps[{index}].agent_id does not reference an agent in this project")
        _validate_template_paths(step.get("input"), f"steps[{index}].input", errors)

    duplicate_ids = sorted({item for item in ids if ids.count(item) > 1})
    for step_id in duplicate_ids:
        errors.append(f"Duplicate step id: {step_id}")

    step_ids = set(ids)
    start_step = definition.get("start_step")
    if start_step and str(start_step) not in step_ids:
        errors.append("start_step must reference an existing step id")
    if not start_step:
        warnings.append("start_step is not set; steps[0] will be used")

    graph: dict[str, list[str]] = {step_id: [] for step_id in step_ids}
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "").strip()
        if not step_id:
            continue

        for next_id in _as_string_list(step.get("next")):
            if next_id not in step_ids:
                errors.append(f"steps[{index}].next references unknown step: {next_id}")
            else:
                graph.setdefault(step_id, []).append(next_id)

        for dependency_id in _as_string_list(step.get("depends_on")):
            if dependency_id not in step_ids:
                errors.append(f"steps[{index}].depends_on references unknown step: {dependency_id}")
            else:
                graph.setdefault(dependency_id, []).append(step_id)

        for route in step.get("routing") or []:
            if not isinstance(route, dict):
                errors.append(f"steps[{index}].routing items must be objects")
                continue
            next_id = route.get("next")
            if next_id is None:
                errors.append(f"steps[{index}].routing.next is required")
                continue
            next_id = str(next_id)
            if next_id not in step_ids:
                errors.append(f"steps[{index}].routing.next references unknown step: {next_id}")
            else:
                graph.setdefault(step_id, []).append(next_id)
        on_error = step.get("on_error")
        if on_error:
            on_error = str(on_error)
            if on_error not in step_ids:
                errors.append(f"steps[{index}].on_error references unknown step: {on_error}")
            else:
                graph.setdefault(step_id, []).append(on_error)

    if _has_cycle(graph):
        errors.append("Workflow graph contains a cycle; workflows must be acyclic")

    _validate_template_paths(definition.get("output"), "output", errors)
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    item = str(value).strip()
    return [item] if item else []

def _validate_template_paths(value: Any, label: str, errors: list[str]) -> None:
    if isinstance(value, str):
        for expr in _TEMPLATE_RE.findall(value):
            path = expr.strip()
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_-]+)*$", path):
                errors.append(f"{label} contains unsupported template expression: {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_template_paths(item, f"{label}[{index}]", errors)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_template_paths(item, f"{label}.{key}", errors)


def _has_cycle(graph: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for child in graph.get(node, []):
            if visit(child):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)
