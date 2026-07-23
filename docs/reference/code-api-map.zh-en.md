# Code and API Map / 代码与 API 对齐参考

状态 / Status: Code-aligned snapshot from the current repository.

本页用于把文档和当前代码事实对齐。后续新增接口、数据表、前端页面或 worker 任务时，优先更新本页，再把细节同步到 guides/modules/nodes。

This page keeps the docs aligned with the current code. When APIs, tables, frontend pages, or worker tasks change, update this page first, then sync details into guides/modules/nodes.

## Repository Map / 仓库地图

| Path | Current responsibility |
| --- | --- |
| `backend/app/main.py` | FastAPI app, CORS, `/health`, `/api` router mount |
| `backend/app/api/v1` | Versioned API modules: auth, projects, resources, provider-connections, chat, memory, registry |
| `backend/app/db/models.py` | SQLAlchemy tables for users, projects, resources, memory, runtime runs/events, provider connections |
| `backend/alembic/versions` | Schema evolution from initial schema through provider connections |
| `backend/app/runtime` | Provider clients, LLM service, executor, embeddings, MCP client, code executor |
| `backend/app/runtime/agent_engine` | ReAct agent, LLM wrapper, and tool manager |
| `backend/app/workers` | Celery app and retry task dispatch |
| `frontend/src/router/index.js` | Frontend routes and auth guard |
| `frontend/src/services/api.js` | Frontend API client and endpoint mapping |
| `frontend/src/views` | Dashboard, login, projects, project detail, resources, workbench |
| `docs` | MkDocs documentation source |

## Backend API Surface / 后端 API 面

Base path: `/api`

| Module | Endpoints |
| --- | --- |
| Health | `GET /health` |
| Auth | `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `GET /api/v1/auth/users/search` |
| Projects | `GET/POST /api/v1/projects`, `GET/PATCH/DELETE /api/v1/projects/{project_id}` |
| Project members | `POST /api/v1/projects/{project_id}/members`, `DELETE /api/v1/projects/{project_id}/members/{member_id}`, `POST /api/v1/projects/{project_id}/member-managers`, `DELETE /api/v1/projects/{project_id}/member-managers/{member_id}` |
| Resources | `GET /api/v1/resources/defaults`, `GET /api/v1/resources/mine`, `POST /api/v1/resources/preview-chat`, `GET/POST /api/v1/resources/projects/{project_id}`, `GET/PATCH/DELETE /api/v1/resources/{resource_id}` |
| Provider connections | `POST /api/v1/provider-connections/projects/{project_id}/probe-models`, `POST /api/v1/provider-connections/projects/{project_id}/test`, `GET/POST /api/v1/provider-connections/projects/{project_id}`, `GET/PATCH/DELETE /api/v1/provider-connections/{connection_id}`, `POST /api/v1/provider-connections/{connection_id}/test` |
| Chat/runtime | `GET /api/v1/chat/agents/{agent_id}/debug`, `GET /api/v1/chat/code-execution-audits`, `POST /api/v1/chat/projects/{project_id}/sessions`, `GET /api/v1/chat/projects/{project_id}/sessions`, `GET /api/v1/chat/sessions/{session_id}/messages`, `GET /api/v1/chat/sessions/{session_id}/runs`, `GET /api/v1/chat/runs/{run_id}/events`, `POST /api/v1/chat/sessions/{session_id}/messages` |
| Memory | `POST /api/v1/memory`, `GET /api/v1/memory`, `POST /api/v1/memory/semantic-search`, `POST /api/v1/memory/retry-embeddings` |
| Registry | `POST /api/v1/registry/projects/{project_id}/{kind}`, `GET /api/v1/registry/projects/{project_id}/{kind}`, `GET /api/v1/registry/public/{kind}`, `POST /api/v1/registry/mcp/probe` |

## Runtime Capabilities / Runtime 能力

| Capability | Current status |
| --- | --- |
| LLM mode | OpenAI-compatible and localhost provider calls |
| Provider profile | Env-prefix mapping such as `ZHIPU_*` or `QWEN_*` |
| Provider Connection | Project-level OpenAI-compatible Base URL + API Key, encrypted at rest |
| Code mode | Executes Agent `custom_code` in a restricted subprocess |
| Tool call | code-mode Agent can call associated Tool via `call_tool(...)` |
| MCP call | code-mode Agent can call associated MCP via `call_mcp(...)` |
| ReAct engine | Optional `engine_type=react` path with thought/action/observation events |
| Runtime timeline | `runtime_runs` and `runtime_run_events` |
| Code audits | `GET /api/v1/chat/code-execution-audits` |
| Worker | Celery queue for embedding retry with API fallback |

## Database Tables / 数据库表

| Area | Tables |
| --- | --- |
| Auth/projects | `users`, `projects`, `project_members`, `project_member_permissions` |
| Resources | `resources`, `provider_connections` |
| Chat/runtime | `chat_sessions`, `chat_messages`, `runtime_runs`, `runtime_run_events` |
| Memory | `memory_records`, `memory_embedding_jobs` |

## Domain Enums / 领域枚举

| Enum | Values |
| --- | --- |
| `Visibility` | `private`, `project`, `public` |
| `ResourceKind` | `agent`, `workflow`, `tool`, `skill`, `mcp`, `knowledge_base` |
| `MemoryType` | `conversation`, `project`, `agent`, `execution`, `global` |
| `MemoryScope` | `conversation`, `project`, `agent`, `execution`, `global` |
| `EmbeddingStatus` | `skipped`, `pending`, `succeeded`, `failed` |

## Frontend Routes / 前端页面

| Route | Purpose |
| --- | --- |
| `/login` | Register/login and token persistence |
| `/` | Dashboard |
| `/projects` | Project list, create/edit/delete, member management entry |
| `/projects/:projectId` | Project detail and project resources |
| `/resources/overview` | Owned resources list |
| `/resources/agents`, `/resources/tools`, `/resources/skills`, `/resources/mcps`, `/resources/knowledge-bases` | Resource lists by kind |
| `/resources/<kind>/create`, `/resources/<kind>/:resourceId/edit` | Resource create/edit forms |
| `/workflows`, `/workflows/create`, `/workflows/:resourceId/edit` | Workflow resource management |
| `/workbench` | Project chat sessions, agent selection, messages, run timeline/events |

## Documentation Maintenance Notes / 文档维护建议

1. Keep `mkdocs.yml` as the authoritative navigation list.
2. Keep module docs for user-facing workflows; keep node docs for architecture and implementation design.
3. Do not delete docs that are linked by `mkdocs.yml` unless the nav is updated in the same change.
4. Treat `README.md`, `README.en.md`, and `README.zh.md` as landing pages; put deeper setup and troubleshooting in `docs/guides`.
5. When code changes API paths, update `frontend/src/services/api.js`, this page, and the relevant guide together.
6. When a roadmap item lands in code, move it from `architecture-roadmap` into this page and the relevant module guide.
