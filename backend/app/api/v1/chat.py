import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from time import perf_counter

from app.api.deps import get_current_user_id, get_db
from app.runtime.code_executor import code_runtime_executor
from app.runtime.llm_service import LLMRequest, llm_service
from app.runtime.mcp_client import (
    extract_tool_result_text,
    get_mcp_client,
    mcp_tool_to_openai,
)
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


def _decode_code_result(code_result: dict | str) -> tuple[str, list[str], list[dict[str, str]], bool]:
    text = code_result.get("text", "") if isinstance(code_result, dict) else str(code_result)
    used_tools = list(code_result.get("used_tools", [])) if isinstance(code_result, dict) else []
    used_mcps = list(code_result.get("used_mcps", [])) if isinstance(code_result, dict) else []
    return str(text), used_tools, used_mcps, llm_service.code_requests_llm(str(text))


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
    provider_connection_id: str | None = None
    provider_connection: dict | None = None
    system_prompt: str | None = None
    run_mode = "llm"
    custom_code = ""
    agent_config: dict = {}
    tools: list[dict] = []
    mcps: list[dict] = []
    if payload.agent_id:
        agent_resource = store.get_agent_resource_for_project(db, session.project_id, payload.agent_id)
        model_provider = agent_resource.model_provider
        model_name = agent_resource.model_name
        agent_config = dict(agent_resource.config or {})
        provider_profile = agent_config.get("provider_profile")
        provider_connection_id = agent_config.get("provider_connection_id")
        if provider_connection_id:
            provider_connection = store.get_provider_connection_runtime_config(
                db,
                connection_id=provider_connection_id,
                actor=user_id,
            )
        system_prompt = agent_config.get("system_prompt")
        run_mode = str(agent_config.get("run_mode") or "llm").strip().lower()
        custom_code = str(agent_config.get("custom_code") or "")
        tools = store.list_tool_resources_for_project(
            db,
            project_id=session.project_id,
            tool_ids=list(agent_config.get("tool_ids") or []),
            actor=user_id,
        )
        mcps = store.list_mcp_resources_for_project(
            db,
            project_id=session.project_id,
            mcp_ids=list(agent_config.get("mcp_ids") or []),
            actor=user_id,
        )
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
                "provider_connection_id": provider_connection_id,
                "run_mode": run_mode,
            },
        )

    try:
        store.append_chat_message(db, session_id, role="user", text=payload.text)
        used_tools: list[str] = []
        used_mcps: list[dict[str, str]] = []
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
            code_result = code_runtime_executor.run(
                payload.text,
                custom_code=custom_code,
                context={
                    "project_id": session.project_id,
                    "session_id": session.id,
                    "user_id": user_id,
                    "agent_id": payload.agent_id,
                    "config": agent_config,
                },
                tools=tools,
                mcps=mcps,
            )
            code_text, used_tools, used_mcps, use_llm = _decode_code_result(code_result)

            if use_llm:
                if provider_connection or model_provider or model_name:
                    llm_response = llm_service.generate(
                        LLMRequest(
                            text=payload.text,
                            model_provider=model_provider,
                            model_name=model_name,
                            provider_profile=provider_profile,
                            provider_connection_id=provider_connection_id,
                            provider_connection=provider_connection,
                            system_prompt=system_prompt,
                        )
                    )
                    answer = llm_response.text
                    store.append_runtime_run_event(
                        db=db,
                        run_id=run.id,
                        stage="llm",
                        status="succeeded" if llm_response.ok else "failed",
                        message="LLM fallback executed from code mode",
                        payload={
                            "provider": llm_response.provider,
                            "model_name": llm_response.model_name,
                            "used_fallback": llm_response.used_fallback,
                            "error": llm_response.error,
                        },
                    )
                else:
                    answer = "[code-fallback-skipped] use_llm requested but model provider/model name is not configured"
            else:
                answer = code_text

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
                    "used_tools": used_tools,
                    "used_mcps": used_mcps,
                },
            )
        else:
            # ------------------------------------------------------------------
            # Fetch tool definitions from associated MCPs (best-effort).
            # ------------------------------------------------------------------
            openai_tools: list[dict] = []
            # Maps OpenAI tool name → (mcp_spec, original_tool_name)
            tool_to_mcp: dict[str, tuple[dict, str]] = {}

            for mcp_spec in mcps:
                mcp_name = str(mcp_spec.get("name") or "")
                try:
                    mcp_c = get_mcp_client(mcp_spec)
                    for tool in mcp_c.list_tools():
                        openai_def = mcp_tool_to_openai(mcp_name, tool)
                        fn_name = openai_def["function"]["name"]
                        openai_tools.append(openai_def)
                        tool_to_mcp[fn_name] = (mcp_spec, str(tool.get("name") or ""))
                except Exception:
                    pass  # skip unreachable MCPs

            # ------------------------------------------------------------------
            # Build initial conversation messages.
            # ------------------------------------------------------------------
            conv_messages: list[dict] = []
            if system_prompt:
                conv_messages.append({"role": "system", "content": system_prompt})
            conv_messages.append({"role": "user", "content": payload.text})

            # ------------------------------------------------------------------
            # Agentic loop: call LLM → execute tool calls → repeat.
            # ------------------------------------------------------------------
            _MAX_TOOL_ITERATIONS = 10
            answer = ""
            llm_response = None

            for _iter in range(_MAX_TOOL_ITERATIONS):
                llm_response = llm_service.generate(
                    LLMRequest(
                        text=payload.text,
                        model_provider=model_provider,
                        model_name=model_name,
                        provider_profile=provider_profile,
                        provider_connection_id=provider_connection_id,
                        provider_connection=provider_connection,
                        system_prompt=system_prompt,
                        messages=conv_messages,
                        tools=openai_tools if openai_tools else None,
                    )
                )

                if llm_response.tool_calls:
                    # Append assistant message with tool_calls to conversation.
                    conv_messages.append({
                        "role": "assistant",
                        "content": llm_response.text or None,
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc["arguments"]),
                                },
                            }
                            for tc in llm_response.tool_calls
                        ],
                    })

                    # Execute each requested tool call.
                    for tc in llm_response.tool_calls:
                        fn_name = tc["name"]
                        fn_args = tc["arguments"]
                        if fn_name in tool_to_mcp:
                            mcp_spec, orig_tool = tool_to_mcp[fn_name]
                            mcp_res_name = str(mcp_spec.get("name") or "")
                            try:
                                raw = get_mcp_client(mcp_spec).call_tool(orig_tool, fn_args)
                                result_text = extract_tool_result_text(raw)
                                used_mcps.append({"mcp": mcp_res_name, "tool": orig_tool})
                                store.append_runtime_run_event(
                                    db=db, run_id=run.id, stage="mcp", status="succeeded",
                                    message=f"MCP tool called: {mcp_res_name}/{orig_tool}",
                                    payload={"mcp": mcp_res_name, "tool": orig_tool},
                                )
                            except Exception as exc:
                                result_text = f"[error calling {fn_name}: {exc}]"
                                store.append_runtime_run_event(
                                    db=db, run_id=run.id, stage="mcp", status="failed",
                                    message=f"MCP tool failed: {fn_name}",
                                    payload={"error": str(exc)},
                                )
                        else:
                            result_text = f"[unknown tool: {fn_name}]"

                        conv_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result_text,
                        })
                else:
                    answer = llm_response.text
                    break
            else:
                answer = (llm_response.text if llm_response else "") or "[max tool iterations reached]"

            store.append_runtime_run_event(
                db=db,
                run_id=run.id,
                stage="llm",
                status="succeeded" if (llm_response and llm_response.ok) else "failed",
                message="LLM generation completed",
                payload={
                    "provider": llm_response.provider if llm_response else "",
                    "model_name": llm_response.model_name if llm_response else "",
                    "used_fallback": llm_response.used_fallback if llm_response else False,
                    "error": llm_response.error if llm_response else None,
                    "tool_iterations": _iter + 1,
                    "mcp_calls": len(used_mcps),
                },
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
        return ChatMessageResponse(
            session_id=session_id,
            role="assistant",
            text=answer,
            run_id=run.id,
            used_tools=used_tools,
            used_mcps=used_mcps,
        )
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
