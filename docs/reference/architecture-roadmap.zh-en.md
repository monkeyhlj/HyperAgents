# Architecture Roadmap (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [代码与 API 对齐](code-api-map.zh-en.md) | [前端指南](../guides/frontend-guide.zh-en.md)

## 1) 当前结论 / Current Conclusion

中文：
HyperAgents 当前已经形成 FastAPI + Vue 3 + View UI Plus 的前后端分离骨架，并完成了项目、资源、运行时间线、Memory、Provider Connection、MCP probe、code-mode Agent 与 Worker fallback/queue 的基础闭环。

English:
HyperAgents now has a FastAPI + Vue 3 + View UI Plus full-stack foundation with project/resource management, runtime timeline, Memory, Provider Connections, MCP probe, code-mode Agents, and Worker fallback/queue support.

## 2) 已落地能力 / Implemented Capabilities

- Project-first domain model and member/member-manager permissions.
- Auth with Bearer token, plus `x-user-id` fallback for local compatibility.
- Unified resources: `agent`, `workflow`, `tool`, `skill`, `mcp`, `knowledge_base`.
- Default resource templates from `backend/app/core/default_resources.json`.
- Runtime runs and runtime run events.
- Workbench session history, message history, run list, event view, Tool/MCP usage tags.
- Agent `llm` mode, `code` mode, and optional `engine_type=react` path.
- Project-level Provider Connections with encrypted API key storage.
- Memory write/search/semantic-search and embedding retry.
- Celery + Redis queue mode for embedding retry, with API-process fallback.
- Alembic migrations through provider connections.

## 3) 当前边界 / Current Boundaries

- Workflow is currently a managed resource definition; there is no dedicated workflow runtime API yet.
- ReAct support exists, but Skills and Knowledge Base tools in the ReAct `ToolManager` are still lightweight or placeholder-level.
- Runtime events exist for runtime/agent/code/tool/mcp paths, but token usage and latency breakdown are not persisted as first-class metrics yet.
- Worker queue is currently focused on embedding retry; there is no task-center API or UI yet.
- Frontend still uses one API service file; domain-split API clients can be introduced later.

## 4) Target Architecture

### 4.1 Backend Logical Split

1. Metadata API
- Projects, users, permissions, resource definitions, provider connections.

2. Runtime API
- Chat sessions, messages, Agent execution, Tool/MCP orchestration, run timeline.

3. Worker
- Async jobs, retries, scheduled jobs, callbacks, long-running execution.

Keep the logical split inside the current monorepo first; split into services only when operational pressure justifies it.

### 4.2 Frontend IA

The frontend should continue toward a project-centered workspace:

- Project Home
- Resources: Agent/Workflow/Tool/Skill/MCP/Knowledge Base
- Workbench: chat/run/events/audits
- Memory
- Settings
- Task Center

Continue using View UI Plus. Prioritize dense operational clarity and observability.

## 5) Next Phases

### Phase A: Runtime Observability

- Persist token usage, latency, provider/model metadata, and retry metadata on runs/events.
- Normalize event stages for `runtime`, `agent`, `code_execution`, `tool`, `mcp`, `memory`, `provider`.
- Add filters for run status, project, agent, and stage.

### Phase B: Task Center

- Add task status APIs for queued/running/succeeded/failed jobs.
- Expose Worker queue state and retry controls in the frontend.
- Move additional long-running work into Worker where useful.

### Phase C: Workflow Runtime

- Define workflow execution schema and runtime API.
- Reuse Runtime Run and Event models for workflow execution.
- Support manual trigger first, then scheduled/webhook triggers.

### Phase D: Resource Ecosystem

- Promote mature Tool/MCP/Skill resources through Registry flows.
- Add versioning/release status for reusable resources.
- Harden sandbox/code execution and external connector governance.

## 6) Repo Refactor Map

Recommended incremental refactors:

1. Split `frontend/src/services/api.js` by domain when it becomes hard to maintain.
2. Extract backend runtime orchestration helpers out of `chat.py` as the execution path grows.
3. Add `tasks` or `jobs` API module before adding a Task Center UI.
4. Keep documentation aligned through [code-api-map.zh-en.md](code-api-map.zh-en.md) whenever routes or runtime behavior change.

## 7) Immediate Documentation Rule

When a feature moves from roadmap to code, update three places in the same change:

1. `reference/code-api-map.zh-en.md`
2. the relevant `modules/` or `guides/` document
3. `reference/api-changelog.zh-en.md`
