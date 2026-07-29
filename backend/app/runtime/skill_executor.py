"""SkillRuntime: execute uploaded Agent Skill scripts in a constrained local workspace."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import SkillExecutionModel
from app.runtime.skill_service import get_skill_package_root, validate_input_output
from app.services.user_file_service import user_file_service

logger = logging.getLogger(__name__)


_RUNNER_SCRIPT = r'''
import base64
import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path


def _json_default(value):
    try:
        from pathlib import Path as _Path
        if isinstance(value, _Path):
            return str(value)
    except Exception:
        pass
    return str(value)


def _collect_output_files(work_dir):
    outputs = Path(work_dir) / "outputs"
    generated = []
    if not outputs.exists():
        return generated
    for path in outputs.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(outputs).as_posix()
        generated.append({
            "filename": rel,
            "content_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
        })
    return generated


def _call_entrypoint(func, input_data, context):
    attempts = [
        lambda: func(input_data=input_data, context=context),
        lambda: func(input_data, context),
        lambda: func(input_data=input_data),
        lambda: func(input_data),
        lambda: func(),
    ]
    last_error = None
    for attempt in attempts:
        try:
            result = attempt()
            if inspect.isawaitable(result):
                raise RuntimeError("Async skill entrypoints are not supported by the local runner yet")
            return result
        except TypeError as exc:
            last_error = exc
            continue
    raise last_error or RuntimeError("Unable to call skill entrypoint")


def main():
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    module_path = Path(payload["module_path"])
    function_name = payload["function_name"]
    work_dir = payload["work_dir"]
    input_data = payload.get("input_data") or {}
    context = payload.get("context") or {}

    os.chdir(work_dir)
    sys.path.insert(0, work_dir)

    spec = importlib.util.spec_from_file_location("skill_entrypoint", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load entrypoint module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    func = getattr(module, function_name, None)
    if not callable(func):
        raise RuntimeError(f"Entrypoint function not callable: {function_name}")

    output = _call_entrypoint(func, input_data, context)
    if output is None:
        output = {}
    if not isinstance(output, dict):
        output = {"result": output}

    collected_files = _collect_output_files(work_dir)
    if collected_files:
        output.setdefault("generated_files", [])
        output["generated_files"].extend(collected_files)

    print(json.dumps({"ok": True, "output_data": output}, ensure_ascii=False, default=_json_default))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
'''


class SkillRuntime:
    """Execute the declared Python entrypoint from an uploaded Skill package.

    This runtime is intentionally conservative: it only executes the frontmatter
    `entrypoint` if the corresponding file exists inside the uploaded Skill
    package. Skills without an executable entrypoint remain instruction-only.
    """

    def __init__(self, db: Session | None = None):
        self.db = db

    def can_execute(self, skill: dict) -> bool:
        try:
            self._resolve_entrypoint(skill)
            return True
        except Exception:
            return False

    def execute(
        self,
        *,
        skill: dict,
        input_data: dict[str, Any],
        context: dict[str, Any] | None = None,
        timeout_seconds: int = 30,
        user_id: str | None = None,
        output_base_dir: str | None = None,
    ) -> dict[str, Any]:
        skill_id = str(skill.get("skill_id") or "")
        started = datetime.utcnow()
        execution_id = self._create_execution(skill, input_data)

        try:
            validate_input_output(input_data, skill.get("input_schema") or {})
        except ValueError as exc:
            result = {"status": "failed", "error_message": f"Input validation failed: {exc}"}
            self._finish_execution(execution_id, "failed", error_message=result["error_message"], started=started)
            return result

        try:
            package_root, module_path, function_name = self._resolve_entrypoint(skill)
        except Exception as exc:
            result = {"status": "skipped", "reason": str(exc), "output_data": {}}
            self._finish_execution(execution_id, "completed", output_data=result, started=started)
            return result

        temp_dir = Path(tempfile.mkdtemp(prefix=f"skill_{skill_id}_"))
        try:
            work_dir = temp_dir / "work"
            shutil.copytree(package_root, work_dir)
            runner_path = temp_dir / "runner.py"
            payload_path = temp_dir / "payload.json"
            runner_path.write_text(_RUNNER_SCRIPT, encoding="utf-8")

            input_files = self._materialize_input_files(
                work_dir=work_dir,
                input_data=input_data,
                user_id=user_id or str((context or {}).get("user_id") or ""),
            )
            runtime_context = dict(context or {})
            runtime_context.update(
                {
                    "skill_id": skill_id,
                    "skill_name": skill.get("name") or skill_id,
                    "work_dir": str(work_dir),
                    "outputs_dir": str(work_dir / "outputs"),
                    "inputs_dir": str(work_dir / "inputs"),
                    "input_files": input_files,
                }
            )
            (work_dir / "outputs").mkdir(parents=True, exist_ok=True)

            payload = {
                "module_path": str(work_dir / module_path.relative_to(package_root)),
                "function_name": function_name,
                "work_dir": str(work_dir),
                "input_data": input_data,
                "context": runtime_context,
            }
            payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(runner_path), str(payload_path)],
                cwd=str(work_dir),
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
            )

            stdout = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            parsed = self._parse_runner_stdout(stdout)
            if proc.returncode != 0 or not parsed.get("ok"):
                error = parsed.get("error") or stderr or stdout or f"Skill process exited with {proc.returncode}"
                result = {"status": "failed", "error_message": error, "stdout": stdout, "stderr": stderr}
                self._finish_execution(execution_id, "failed", error_message=error, started=started)
                return result

            output_data = parsed.get("output_data") or {}
            try:
                validate_input_output(output_data, skill.get("output_schema") or {})
            except ValueError as exc:
                logger.warning("Skill output validation warning: %s", exc)

            saved_files: list[str] = []
            generated_files = output_data.get("generated_files")
            if user_id and output_base_dir and isinstance(generated_files, list):
                saved_files = user_file_service.save_generated_files(user_id, output_base_dir, generated_files)
                output_data["saved_files"] = saved_files

            result = {
                "status": "completed",
                "output_data": output_data,
                "saved_files": saved_files,
                "stdout": stdout,
                "stderr": stderr,
                "execution_id": execution_id,
            }
            self._finish_execution(execution_id, "completed", output_data=output_data, started=started)
            return result
        except subprocess.TimeoutExpired:
            error = f"Skill execution timeout after {timeout_seconds}s"
            self._finish_execution(execution_id, "failed", error_message=error, started=started)
            return {"status": "failed", "error_message": error, "execution_id": execution_id}
        except Exception as exc:
            error = f"Skill execution failed: {exc}"
            logger.error(error, exc_info=True)
            self._finish_execution(execution_id, "failed", error_message=error, started=started)
            return {"status": "failed", "error_message": error, "execution_id": execution_id}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _materialize_input_files(*, work_dir: Path, input_data: dict[str, Any], user_id: str | None) -> list[dict[str, str]]:
        files = input_data.get("files") or []
        if not user_id or not isinstance(files, list):
            return []

        inputs_dir = work_dir / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        materialized: list[dict[str, str]] = []
        used_names: set[str] = set()

        for index, relative_path in enumerate(files, start=1):
            try:
                source = user_file_service.get_file_for_download(user_id, str(relative_path))
            except Exception as exc:
                materialized.append({
                    "source_path": str(relative_path),
                    "error": str(exc),
                })
                continue

            base_name = source.name or f"input_{index}"
            target_name = base_name
            if target_name in used_names:
                target_name = f"{index}_{base_name}"
            used_names.add(target_name)
            target = inputs_dir / target_name
            shutil.copy2(source, target)
            materialized.append({
                "source_path": str(relative_path),
                "local_path": str(target),
                "filename": target_name,
            })

        input_data.setdefault("input_files", materialized)
        return materialized
    def _resolve_entrypoint(self, skill: dict) -> tuple[Path, Path, str]:
        skill_id = str(skill.get("skill_id") or "")
        if not skill_id:
            raise ValueError("Skill id is missing")

        entrypoint = str(skill.get("entrypoint") or "").strip()
        if not entrypoint or ":" not in entrypoint:
            raise ValueError("Skill has no executable entrypoint")

        module_part, function_name = entrypoint.split(":", 1)
        function_name = function_name.strip()
        module_rel = module_part.strip().replace("\\", "/")
        if not module_rel or not function_name:
            raise ValueError("Skill entrypoint is incomplete")
        if ".." in Path(module_rel).parts:
            raise ValueError("Skill entrypoint escapes package")
        if not module_rel.endswith(".py"):
            module_rel = f"{module_rel}.py"

        package_root = get_skill_package_root(skill_id)
        module_path = (package_root / module_rel).resolve()
        try:
            module_path.relative_to(package_root)
        except ValueError as exc:
            raise ValueError("Skill entrypoint escapes package") from exc
        if not module_path.exists() or not module_path.is_file():
            raise FileNotFoundError(f"Skill entrypoint file not found: {module_rel}")
        return package_root, module_path, function_name

    @staticmethod
    def _parse_runner_stdout(stdout: str) -> dict[str, Any]:
        if not stdout:
            return {}
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
        return {}

    def _create_execution(self, skill: dict, input_data: dict[str, Any]) -> str | None:
        if not self.db:
            return None
        try:
            execution = SkillExecutionModel(
                id=str(uuid4()),
                skill_id=str(skill.get("skill_id")),
                agent_id=str(input_data.get("agent_id") or "") or None,
                project_id=str(input_data.get("project_id") or skill.get("project_id") or ""),
                session_id=str(input_data.get("session_id") or "") or None,
                status="running",
                input_data=input_data,
                started_at=datetime.utcnow(),
            )
            self.db.add(execution)
            self.db.commit()
            return execution.id
        except Exception:
            logger.warning("Failed to create skill execution record", exc_info=True)
            self.db.rollback()
            return None

    def _finish_execution(
        self,
        execution_id: str | None,
        status: str,
        *,
        output_data: dict[str, Any] | None = None,
        error_message: str | None = None,
        started: datetime | None = None,
    ) -> None:
        if not self.db or not execution_id:
            return
        try:
            execution = self.db.get(SkillExecutionModel, execution_id)
            if not execution:
                return
            completed = datetime.utcnow()
            execution.status = status
            execution.output_data = output_data
            execution.error_message = error_message
            execution.completed_at = completed
            if started:
                execution.execution_time_ms = int((completed - started).total_seconds() * 1000)
            self.db.commit()
        except Exception:
            logger.warning("Failed to finish skill execution record", exc_info=True)
            self.db.rollback()


# Backwards-compatible class names for existing imports.
class SkillExecutor(SkillRuntime):
    pass


class PythonVenvExecutor(SkillRuntime):
    pass


class DockerExecutor(SkillRuntime):
    pass