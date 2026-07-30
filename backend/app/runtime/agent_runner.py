from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ResourceModel
from app.runtime.agent_engine import LangChainLLMWrapper, ReActAgent, ToolManager
from app.runtime.knowledge_service import KnowledgeService
from app.runtime.llm_service import LLMRequest, llm_service
from app.runtime.skill_activation import skill_activation_engine
from app.runtime.skill_loader import build_skill_catalog_text, skill_display_name
from app.services.postgres_store import store

logger = logging.getLogger(__name__)


@dataclass
class AgentRunResult:
    text: str
    agent_id: str
    agent_name: str
    events: list[dict] = field(default_factory=list)
    used_tools: list[str] = field(default_factory=list)
    used_mcps: list[dict[str, str]] = field(default_factory=list)
    used_skills: list[str] = field(default_factory=list)
    used_knowledge_bases: list[str] = field(default_factory=list)


class AgentRunner:
    """Run one ResourceKind.AGENT for chat/workflow style orchestration."""

    async def run_agent(
        self,
        db: Session,
        *,
        project_id: str,
        agent_id: str,
        user_id: str,
        input_text: str,
        session_id: str | None = None,
        workflow_run_id: str | None = None,
        extra_context: dict | None = None,
    ) -> AgentRunResult:
        agent_resource = store.get_agent_resource_for_project(db, project_id, agent_id)
        agent_config = dict(agent_resource.config or {})
        model_provider = agent_resource.model_provider
        model_name = agent_resource.model_name
        provider_profile = agent_config.get("provider_profile")
        provider_connection_id = agent_config.get("provider_connection_id")
        provider_connection = None
        if provider_connection_id:
            provider_connection = store.get_provider_connection_runtime_config(
                db,
                connection_id=provider_connection_id,
                actor=user_id,
            )

        system_prompt = str(agent_config.get("system_prompt") or "").strip() or None
        tools = store.list_tool_resources_for_project(
            db,
            project_id=project_id,
            tool_ids=[str(item) for item in (agent_config.get("tool_ids") or []) if item],
            actor=user_id,
        )
        mcp_ids = _normalize_ids(agent_config.get("mcp_ids") or [])
        mcps = store.list_mcp_resources_for_project(db, project_id=project_id, mcp_ids=mcp_ids, actor=user_id)

        bound_skills = store.list_skill_resources_for_agent(db, project_id=project_id, agent_id=agent_id, actor=user_id)
        config_skills = store.list_skill_resources_for_project(
            db,
            project_id=project_id,
            skill_ids=[str(item) for item in (agent_config.get("skill_ids") or []) if item],
            actor=user_id,
        )
        bound_skills = _merge_skills(bound_skills, config_skills)
        used_skills: list[str] = []
        if bound_skills:
            activation = skill_activation_engine.activate(input_text, bound_skills)
            activated_names = set(activation.activated_names or [])
            used_skills = list(activation.activated_names or [])
            skill_prompt = activation.discovery_prompt
            if activated_names:
                skill_prompt = f"{skill_prompt}\n\nActivated Skills: {', '.join(sorted(activated_names))}"
            catalog = build_skill_catalog_text(bound_skills)
            if catalog:
                skill_prompt = f"{skill_prompt}\n\n{catalog}\nUse the load_skill tool before following detailed Skill workflows."
            system_prompt = f"{system_prompt}\n\n{skill_prompt}" if system_prompt else skill_prompt

        used_knowledge_bases: list[str] = []
        rag_context = await self._build_rag_context(db, agent_resource, agent_config, input_text)
        if rag_context:
            kb_prompt = (
                "You have access to the following knowledge base content relevant to the user's task:\n\n"
                f"{rag_context}\n\nUse it when it is relevant and cite source documents when possible."
            )
            system_prompt = f"{system_prompt}\n\n{kb_prompt}" if system_prompt else kb_prompt
            used_knowledge_bases = [str(item) for item in (agent_config.get("knowledge_base_ids") or []) if item]

        engine_type = str(agent_config.get("engine_type") or "legacy").strip().lower()
        if engine_type == "legacy" and (tools or mcps or bound_skills):
            engine_type = "react"

        context = {
            "mcps": {m.get("id"): m for m in mcps},
            "tools": {t.get("id"): t for t in tools},
            "skills": {
                s.get("skill_id"): {
                    **s,
                    "_runtime_context": {
                        "project_id": project_id,
                        "session_id": session_id,
                        "workflow_run_id": workflow_run_id,
                        "agent_id": agent_id,
                        "user_id": user_id,
                        "output_base_dir": f"generated/{_safe_name(skill_display_name(s))}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                        "timeout_seconds": int((s.get("instance_config") or {}).get("timeout_seconds") or 30),
                    },
                }
                for s in bound_skills
                if s.get("skill_id")
            },
            "knowledge_bases": {},
            "workflow": extra_context or {},
        }
        agent_config = {**agent_config, "skill_ids": [s.get("skill_id") for s in bound_skills if s.get("skill_id")]}

        if engine_type == "react":
            llm_wrapper = LangChainLLMWrapper(
                llm_service=llm_service,
                model_name=model_name or "gpt-4o-mini",
                temperature=float(agent_config.get("temperature", 0.2)),
                provider=model_provider or "openai",
                provider_profile=provider_profile,
                provider_connection_id=provider_connection_id,
                provider_connection=provider_connection,
            )
            react_agent = ReActAgent(
                llm=llm_wrapper,
                tool_manager=ToolManager(),
                max_iterations=int(agent_config.get("max_iterations", 10)),
            )
            answer, events = await react_agent.run(
                user_input=input_text,
                agent_config=agent_config,
                context=context,
                system_prompt=system_prompt,
            )
            return AgentRunResult(
                text=answer,
                agent_id=agent_id,
                agent_name=agent_resource.name,
                events=events,
                used_tools=_extract_used_tools(events),
                used_mcps=[{"id": str(m.get("id")), "name": str(m.get("name"))} for m in mcps],
                used_skills=used_skills,
                used_knowledge_bases=used_knowledge_bases,
            )

        response = llm_service.generate(
            LLMRequest(
                text=input_text,
                model_provider=model_provider,
                model_name=model_name,
                provider_profile=provider_profile,
                provider_connection_id=provider_connection_id,
                provider_connection=provider_connection,
                system_prompt=system_prompt,
            )
        )
        answer = response.text
        if not response.ok:
            answer = f"Agent execution failed: {response.error or response.text}"
        return AgentRunResult(
            text=answer,
            agent_id=agent_id,
            agent_name=agent_resource.name,
            events=[{"stage": "llm", "status": "succeeded" if response.ok else "failed", "provider": response.provider, "model_name": response.model_name}],
            used_tools=[],
            used_mcps=[{"id": str(m.get("id")), "name": str(m.get("name"))} for m in mcps],
            used_skills=used_skills,
            used_knowledge_bases=used_knowledge_bases,
        )

    async def _build_rag_context(self, db: Session, agent_resource: ResourceModel, agent_config: dict, input_text: str) -> str:
        knowledge_base_ids = [str(item) for item in (agent_config.get("knowledge_base_ids") or []) if item]
        if not knowledge_base_ids:
            return ""
        try:
            query_embedding = None
            try:
                embeddings = await KnowledgeService.get_embeddings(
                    texts=[input_text],
                    model="embedding-3",
                    embedding_provider="openai",
                )
                if embeddings:
                    query_embedding = embeddings[0]
            except Exception as exc:
                logger.warning("Workflow AgentRunner embedding failed; using text search: %s", exc)
            return await KnowledgeService.build_rag_context(
                db=db,
                agent_id=agent_resource.id,
                query_text=input_text,
                query_embedding=query_embedding,
                knowledge_base_ids=knowledge_base_ids,
            )
        except Exception as exc:
            logger.warning("Workflow AgentRunner RAG retrieval failed: %s", exc, exc_info=True)
            return ""


def _normalize_ids(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [raw] if raw else []
    return [str(item) for item in (raw or []) if item]


def _merge_skills(*groups: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for group in groups:
        for item in group:
            key = str(item.get("skill_id") or "")
            if key and key not in merged:
                merged[key] = item
    return list(merged.values())


def _safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_") or "skill"


def _extract_used_tools(events: list[dict]) -> list[str]:
    names: list[str] = []
    for event in events:
        name = str(event.get("tool_name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names
