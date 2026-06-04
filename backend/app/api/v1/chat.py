from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from time import perf_counter

from app.api.deps import get_current_user_id, get_db
from app.runtime.code_executor import code_runtime_executor
from app.runtime.executor import runtime_executor
from app.schemas.resource import (
    CodeExecutionAuditRecord,
    ChatMessageRecord,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionRecord,
    RuntimeRunEventRecord,
    RuntimeRunRecord,
)
from app.services.postgres_store import store


router = APIRouter()


@router.get("/code-execution-audits", response_model=list[CodeExecutionAuditRecord])
def list_code_execution_audits(
    project_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    return store.list_code_execution_audits(db, user_id=user_id, project_id=project_id, limit=limit)


@router.post("/projects/{project_id}/sessions")
def create_chat_session(
    project_id: str,
    payload: ChatSessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    return store.create_chat_session(db, project_id, user_id, payload.title)


@router.get("/projects/{project_id}/sessions", response_model=list[ChatSessionRecord])
def list_chat_sessions(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    return store.list_chat_sessions(db, project_id, user_id, limit=limit)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRecord])
def list_chat_messages(
    session_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    return store.list_chat_messages_for_user(db, session_id, user_id, limit=limit)


@router.get("/sessions/{session_id}/runs", response_model=list[RuntimeRunRecord])
def list_runtime_runs(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    return store.list_runtime_runs_for_session(db, session_id, user_id, limit=limit)


@router.get("/runs/{run_id}/events", response_model=list[RuntimeRunEventRecord])
def list_runtime_run_events(
    run_id: str,
    limit: int = Query(default=500, ge=1, le=1000),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    return store.list_runtime_run_events(db, run_id, user_id, limit=limit)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
def send_message(
    session_id: str,
    payload: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    session = store.get_chat_session_for_user(db, session_id, user_id)
    run = store.create_runtime_run(
        db=db,
        session=session,
        user_id=user_id,
        input_text=payload.text,
        agent_id=payload.agent_id,
    )
    store.append_runtime_run_event(
        db=db,
        run_id=run.id,
        stage="runtime",
        status="running",
        message="Runtime execution started",
        payload={"session_id": session.id},
    )

    model_provider: str | None = None
    model_name: str | None = None
    provider_profile: str | None = None
    system_prompt: str | None = None
    run_mode = "llm"
    custom_code = ""
    agent_config: dict = {}
    if payload.agent_id:
        agent_resource = store.get_agent_resource_for_project(db, session.project_id, payload.agent_id)
        model_provider = agent_resource.model_provider
        model_name = agent_resource.model_name
        agent_config = dict(agent_resource.config or {})
        provider_profile = agent_config.get("provider_profile")
        system_prompt = agent_config.get("system_prompt")
        run_mode = str(agent_config.get("run_mode") or "llm").strip().lower()
        custom_code = str(agent_config.get("custom_code") or "")
        store.append_runtime_run_event(
            db=db,
            run_id=run.id,
            stage="agent",
            status="selected",
            message="Agent selected for runtime",
            payload={
                "agent_id": payload.agent_id,
                "model_provider": model_provider,
                "model_name": model_name,
                "run_mode": run_mode,
            },
        )

    try:
        store.append_chat_message(db, session_id, role="user", text=payload.text)
        if run_mode == "code":
            started = perf_counter()
            preview = payload.text[:200]
            store.append_runtime_run_event(
                db=db,
                run_id=run.id,
                stage="code_execution",
                status="running",
                message="Code execution started",
                payload={"input_preview": preview},
            )
            answer = code_runtime_executor.run(
                payload.text,
                custom_code=custom_code,
                context={
                    "project_id": session.project_id,
                    "session_id": session.id,
                    "user_id": user_id,
                    "agent_id": payload.agent_id,
                    "config": agent_config,
                },
            )
            duration_ms = int((perf_counter() - started) * 1000)
            store.append_runtime_run_event(
                db=db,
                run_id=run.id,
                stage="code_execution",
                status="succeeded",
                message="Code execution succeeded",
                payload={
                    "duration_ms": duration_ms,
                    "input_preview": preview,
                    "output_length": len(answer),
                },
            )
        else:
            answer = runtime_executor.run_chat(
                payload.text,
                model_provider=model_provider,
                model_name=model_name,
                provider_profile=provider_profile,
                system_prompt=system_prompt,
            )
        store.append_chat_message(db, session_id, role="assistant", text=answer)
        store.finish_runtime_run(
            db=db,
            run_id=run.id,
            status="succeeded",
            output_text=answer,
            error=None,
        )
        store.append_runtime_run_event(
            db=db,
            run_id=run.id,
            stage="runtime",
            status="succeeded",
            message="Runtime execution completed",
            payload={"output_length": len(answer)},
        )
        return ChatMessageResponse(session_id=session_id, role="assistant", text=answer, run_id=run.id)
    except Exception as exc:
        error_text = str(exc)
        if run_mode == "code":
            store.append_runtime_run_event(
                db=db,
                run_id=run.id,
                stage="code_execution",
                status="failed",
                message="Code execution failed",
                payload={
                    "error": error_text,
                    "input_preview": payload.text[:200],
                },
            )
        store.finish_runtime_run(
            db=db,
            run_id=run.id,
            status="failed",
            output_text=None,
            error=error_text,
        )
        store.append_runtime_run_event(
            db=db,
            run_id=run.id,
            stage="runtime",
            status="failed",
            message="Runtime execution failed",
            payload={"error": error_text},
        )
        raise
