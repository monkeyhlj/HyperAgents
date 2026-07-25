import json
import logging

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
from app.runtime.knowledge_service import KnowledgeService
from app.runtime.providers import _supports_function_calling
from app.runtime.agent_engine import LangChainLLMWrapper, ReActAgent, ToolManager
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

logger = logging.getLogger(__name__)
router = APIRouter()


def _decode_code_result(code_result: dict | str) -> tuple[str, list[str], list[dict[str, str]], bool]:
    text = code_result.get("text", "") if isinstance(code_result, dict) else str(code_result)
    used_tools = list(code_result.get("used_tools", [])) if isinstance(code_result, dict) else []
    used_mcps = list(code_result.get("used_mcps", [])) if isinstance(code_result, dict) else []
    return str(text), used_tools, used_mcps, llm_service.code_requests_llm(str(text))


@router.get("/agents/{agent_id}/debug", tags=["debug"])
def debug_agent_config(
    agent_id: str,
    project_id: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    """Debug endpoint: return agent config and associated resources."""
    agent = store.get_agent_resource_for_project(db, project_id, agent_id)
    config = dict(agent.config or {})
    mcp_ids = list(config.get("mcp_ids") or [])
    
    # Ensure mcp_ids is a list of strings
    mcp_ids = [str(mid) for mid in mcp_ids if mid]
    
    mcps = store.list_mcp_resources_for_project(db, project_id=project_id, mcp_ids=mcp_ids, actor=user_id)
    
    tools_preview: list[dict] = []
    for mcp_spec in mcps:
        mcp_name = str(mcp_spec.get("name") or "")
        try:
            client = get_mcp_client(mcp_spec)
            tools = client.list_tools()
            tools_preview.append({
                "mcp_name": mcp_name,
                "mcp_id": mcp_spec.get("id"),
                "endpoint_url": mcp_spec.get("endpoint_url"),
                "transport": mcp_spec.get("transport"),
                "tool_count": len(tools),
                "tools": [{"name": t.get("name"), "description": t.get("description", "")} for t in tools[:3]],  # first 3
            })
        except Exception as exc:
            tools_preview.append({
                "mcp_name": mcp_name,
                "mcp_id": mcp_spec.get("id"),
                "error": str(exc),
            })
    
    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "model_provider": agent.model_provider,
        "model_name": agent.model_name,
        "run_mode": config.get("run_mode", "llm"),
        "system_prompt": config.get("system_prompt", ""),
        "mcp_ids_in_config": mcp_ids,
        "mcps_count": len(mcps),
        "mcps": tools_preview,
    }


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
async def send_message(
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
    used_knowledge_bases: list[str] = []  # initialize before agent_id block
    if payload.agent_id:
        agent_resource = store.get_agent_resource_for_project(db, session.project_id, payload.agent_id)
        model_provider = agent_resource.model_provider
        model_name = agent_resource.model_name
        agent_config = dict(agent_resource.config or {})
        logger.info(f"[send_message] Agent resource loaded: id={payload.agent_id}, raw_config={agent_resource.config}")
        # Override agent config with request parameters if provided
        if payload.engine_type:
            agent_config["engine_type"] = payload.engine_type
        if payload.provider_profile:
            agent_config["provider_profile"] = payload.provider_profile
        if payload.temperature is not None:
            agent_config["temperature"] = payload.temperature
        if payload.max_iterations is not None:
            agent_config["max_iterations"] = payload.max_iterations
        if payload.mcp_ids is not None:
            agent_config["mcp_ids"] = payload.mcp_ids
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
        # Ensure mcp_ids is a list of strings; convert from string if needed
        raw_mcp_ids = agent_config.get("mcp_ids") or []
        mcp_ids_list: list[str] = []
        if isinstance(raw_mcp_ids, str):
            # Handle case where mcp_ids was stored as a single string
            mcp_ids_list = [raw_mcp_ids] if raw_mcp_ids else []
        else:
            mcp_ids_list = [str(mid) for mid in raw_mcp_ids if mid]
        
        logger.info(f"[send_message] Agent {payload.agent_id} config: {agent_config}")
        logger.info(f"[send_message] Agent {payload.agent_id} has mcp_ids (raw): {raw_mcp_ids}")
        logger.info(f"[send_message] Agent {payload.agent_id} has mcp_ids (list): {mcp_ids_list}")
        
        mcps = store.list_mcp_resources_for_project(
            db,
            project_id=session.project_id,
            mcp_ids=mcp_ids_list,
            actor=user_id,
        )
        logger.info(f"[send_message] Loaded {len(mcps)} MCPs: {[m.get('name') for m in mcps]}")
        
        # RAG: Load and retrieve from knowledge bases
        knowledge_base_ids = list(agent_config.get("knowledge_base_ids") or [])
        rag_context = ""
        used_knowledge_bases = []
        
        if knowledge_base_ids:
            logger.info(f"[send_message] Agent has {len(knowledge_base_ids)} knowledge bases: {knowledge_base_ids}")
            try:
                # Generate embedding for user query (optional - text search fallback if fails)
                query_embedding = None
                try:
                    emb_result = await KnowledgeService.get_embeddings(
                        texts=[payload.text],
                        model="embedding-3",
                        embedding_provider="openai",
                    )
                    if emb_result and len(emb_result) > 0:
                        query_embedding = emb_result[0]
                except Exception as emb_err:
                    logger.warning(f"[send_message] Embedding failed, using text search: {emb_err}")

                # Build RAG context (vector search if embedding available, else text search)
                rag_context = await KnowledgeService.build_rag_context(
                    db=db,
                    agent_id=payload.agent_id,
                    query_text=payload.text,
                    query_embedding=query_embedding,
                    knowledge_base_ids=knowledge_base_ids,
                )
                
                if rag_context.strip():
                    logger.info(f"[send_message] RAG context retrieved: {len(rag_context)} chars")
                    # Inject RAG context into system prompt
                    kb_prompt = f"""
You have access to the following knowledge base content relevant to the user's query:

{rag_context}

Use this information to provide accurate and informed responses. When relevant, cite the source documents."""
                    
                    if system_prompt:
                        system_prompt = f"{system_prompt}\n\n{kb_prompt}"
                    else:
                        system_prompt = kb_prompt
                    
                    # Track which knowledge bases were used
                    used_knowledge_bases = knowledge_base_ids
                else:
                    logger.info(f"[send_message] No relevant content found in knowledge bases for this query")
            except Exception as e:
                logger.warning(f"[send_message] Failed to retrieve RAG context: {str(e)}", exc_info=True)
        
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
                "used_knowledge_bases": used_knowledge_bases,
            },
        )
    else:
        # No agent_id provided, apply request parameters to agent_config
        if payload.engine_type:
            agent_config["engine_type"] = payload.engine_type
        if payload.provider_profile:
            agent_config["provider_profile"] = payload.provider_profile
        if payload.temperature is not None:
            agent_config["temperature"] = payload.temperature
        if payload.max_iterations is not None:
            agent_config["max_iterations"] = payload.max_iterations
        if payload.mcp_ids is not None:
            agent_config["mcp_ids"] = payload.mcp_ids

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
            # NEW: ReAct Engine (Phase 1 - supports any OpenAI-compatible model)
            # ------------------------------------------------------------------
            engine_type = str(agent_config.get("engine_type", "legacy")).strip().lower()
            
            # Auto-enable ReAct engine if MCPs are present
            if not engine_type or engine_type == "legacy":
                mcp_ids_check = agent_config.get("mcp_ids") or []
                if mcp_ids_check and len(mcp_ids_check) > 0:
                    engine_type = "react"
                    logger.info(f"[send_message] Auto-enabling ReAct engine due to presence of MCPs")
            
            logger.info(f"[send_message] engine_type resolved to: '{engine_type}'")
            
            if engine_type == "react":
                logger.info(f"[send_message] ✓ Using ReAct Agent Engine (agent={payload.agent_id})")
                try:
                    # Initialize ReAct Agent
                    llm_wrapper = LangChainLLMWrapper(
                        llm_service=llm_service,
                        model_name=model_name or "gpt-4o-mini",
                        temperature=float(agent_config.get("temperature", 0.2)),
                        provider=model_provider or "openai",
                        provider_profile=provider_profile,
                        provider_connection_id=provider_connection_id,
                        provider_connection=provider_connection,
                    )
                    tool_manager = ToolManager()
                    agent = ReActAgent(
                        llm=llm_wrapper,
                        tool_manager=tool_manager,
                        max_iterations=int(agent_config.get("max_iterations", 10)),
                    )
                    
                    # Prepare context for agent
                    agent_context = {
                        "mcps": {m.get("id"): m for m in mcps},
                        "tools": {t.get("id"): t for t in tools},
                        "skills": {},  # TODO: Phase 2
                        "knowledge_bases": {},  # TODO: Phase 2
                    }
                    
                    # Run agent
                    answer, agent_events = await agent.run(
                        user_input=payload.text,
                        agent_config=agent_config,
                        context=agent_context,
                        system_prompt=system_prompt,
                    )
                    
                    # Record agent events in RuntimeRunEvent
                    for event in agent_events:
                        store.append_runtime_run_event(
                            db=db,
                            run_id=run.id,
                            stage=f"agentic_{event['stage']}",
                            status="succeeded" if event.get("error") is None else "failed",
                            message=f"Agent step: {event['stage']} (iteration {event.get('iteration', 0)})",
                            payload=event,
                        )
                    
                    logger.info(f"[send_message] ReAct Agent completed with {len(agent_events)} events")
                    
                except Exception as e:
                    logger.error(f"[send_message] ReAct Agent failed: {str(e)}", exc_info=True)
                    answer = f"[ReAct Agent Error] {str(e)}"
                    store.append_runtime_run_event(
                        db=db,
                        run_id=run.id,
                        stage="agent",
                        status="failed",
                        message="ReAct Agent execution failed",
                        payload={"error": str(e)},
                    )
            else:
                # ------------------------------------------------------------------
                # LEGACY: Original agentic loop (function calling based)
                # ------------------------------------------------------------------
                logger.info(f"[send_message] ✗ Using LEGACY engine (engine_type={engine_type}, agent={payload.agent_id})")
                # Check if model supports function calling.
                # ------------------------------------------------------------------
                supports_fc = _supports_function_calling(model_name or "")
                logger.info(f"[send_message] Model {model_name} supports function calling: {supports_fc}")
                
                if not supports_fc and mcps:
                    # Model doesn't support function calling. Fallback to direct LLM call.
                    logger.info(f"[send_message] Model doesn't support function calling. Calling LLM without tools.")
                    llm_response = llm_service.generate(
                        LLMRequest(
                            text=payload.text,
                            model_provider=model_provider,
                            model_name=model_name,
                            provider_profile=provider_profile,
                            provider_connection_id=provider_connection_id,
                            provider_connection=provider_connection,
                            system_prompt=system_prompt,
                            messages=None,  # Use simple single-turn
                            tools=None,  # Don't send tools
                        )
                    )
                    answer = llm_response.text
                    store.append_runtime_run_event(
                        db=db,
                        run_id=run.id,
                        stage="llm",
                        status="succeeded" if llm_response.ok else "failed",
                        message="LLM generation completed (model doesn't support function calling)",
                        payload={
                            "provider": llm_response.provider,
                            "model_name": llm_response.model_name,
                            "note": f"MCPs available but not used: {[m.get('name') for m in mcps]}",
                        },
                    )
                else:
                    # ------------------------------------------------------------------
                    # Fetch tool definitions from associated MCPs (best-effort).
                    # ------------------------------------------------------------------
                    openai_tools: list[dict] = []
                    # Maps OpenAI tool name → (mcp_spec, original_tool_name)
                    tool_to_mcp: dict[str, tuple[dict, str]] = {}
                    mcp_names_for_prompt: list[str] = []

                    for mcp_spec in mcps:
                        mcp_name = str(mcp_spec.get("name") or "")
                        try:
                            mcp_c = get_mcp_client(mcp_spec)
                            tools_list = mcp_c.list_tools()
                            logger.info(f"[send_message] MCP {mcp_name} has {len(tools_list)} tools")
                            if tools_list:
                                mcp_names_for_prompt.append(mcp_name)
                            for tool in tools_list:
                                openai_def = mcp_tool_to_openai(mcp_name, tool)
                                fn_name = openai_def["function"]["name"]
                                openai_tools.append(openai_def)
                                tool_to_mcp[fn_name] = (mcp_spec, str(tool.get("name") or ""))
                        except Exception as exc:
                            # Log but don't fail; other MCPs may still work
                            logger.warning(f"[send_message] Failed to load MCP {mcp_name}: {exc}")

                    # ------------------------------------------------------------------
                    # Augment system prompt with available tools info.
                    # ------------------------------------------------------------------
                    final_system_prompt = system_prompt or "You are a helpful assistant."
                    if mcp_names_for_prompt:
                        tools_list_text = ", ".join(mcp_names_for_prompt)
                        augmented_prompt = f"{final_system_prompt}\n\nYou have access to the following MCP tools/services: {tools_list_text}. When appropriate, use these tools to answer user questions and get real-time information."
                    else:
                        augmented_prompt = final_system_prompt

                    # ------------------------------------------------------------------
                    # Build initial conversation messages.
                    # ------------------------------------------------------------------
                    conv_messages: list[dict] = []
                    conv_messages.append({"role": "system", "content": augmented_prompt})
                    conv_messages.append({"role": "user", "content": payload.text})

                    # ------------------------------------------------------------------
                    # Agentic loop: call LLM → execute tool calls → repeat.
                    # ------------------------------------------------------------------
                    _MAX_TOOL_ITERATIONS = 10
                    answer = ""
                    llm_response = None
                    
                    logger.info(f"[send_message] Starting agentic loop with {len(openai_tools)} tools, prompt includes: {mcp_names_for_prompt}")

                    for _iter in range(_MAX_TOOL_ITERATIONS):
                        logger.debug(f"[send_message] Agentic iteration {_iter + 1}")
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
                            logger.info(f"[send_message] LLM requested {len(llm_response.tool_calls)} tool calls")
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
                                logger.debug(f"[send_message] Executing tool: {fn_name}")
                                if fn_name in tool_to_mcp:
                                    mcp_spec, orig_tool = tool_to_mcp[fn_name]
                                    mcp_res_name = str(mcp_spec.get("name") or "")
                                    try:
                                        raw = get_mcp_client(mcp_spec).call_tool(orig_tool, fn_args)
                                        result_text = extract_tool_result_text(raw)
                                        used_mcps.append({"mcp": mcp_res_name, "tool": orig_tool})
                                        logger.info(f"[send_message] Tool call succeeded: {mcp_res_name}/{orig_tool}")
                                        store.append_runtime_run_event(
                                            db=db, run_id=run.id, stage="mcp", status="succeeded",
                                            message=f"MCP tool called: {mcp_res_name}/{orig_tool}",
                                            payload={"mcp": mcp_res_name, "tool": orig_tool},
                                        )
                                    except Exception as exc:
                                        result_text = f"[error calling {fn_name}: {exc}]"
                                        logger.error(f"[send_message] Tool call failed: {fn_name}, error: {exc}")
                                        store.append_runtime_run_event(
                                            db=db, run_id=run.id, stage="mcp", status="failed",
                                            message=f"MCP tool failed: {fn_name}",
                                            payload={"error": str(exc)},
                                        )
                                else:
                                    result_text = f"[unknown tool: {fn_name}]"
                                    logger.warning(f"[send_message] Unknown tool: {fn_name}")

                                conv_messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": result_text,
                                })
                        else:
                            answer = llm_response.text
                            logger.info(f"[send_message] LLM returned final answer (iteration {_iter + 1})")
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
            used_knowledge_bases=used_knowledge_bases,
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
