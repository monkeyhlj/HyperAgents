# Code and API Map / 代码与 API 对齐参考

状态 / Status: Code-aligned snapshot from the current repository.

本页用于把文档和当前代码事实对齐。后续新增接口、数据表、前端页面或 worker 任务时，优先更新本页，再把细节同步到 guides/modules/nodes。

This page keeps the docs aligned with the current code. When APIs, tables, frontend pages, or worker tasks change, update this page first, then sync details into guides/modules/nodes.

## Repository Map / 仓库地图

| Path | Current responsibility |
| --- | --- |
| `backend/app/main.py` | FastAPI app, CORS, HTTP logging middleware, `/health`, `/api` router mount, startup tasks |
| `backend/app/api/v1` | Versioned API modules: auth, projects, resources, provider-connections, chat, files, memory, registry, knowledge, skills, workflows |
| `backend/app/db/models.py` | SQLAlchemy models for users, projects, resources, workflows, chat/runtime, memory, knowledge, skills, provider connections |
| `backend/app/db/schema.py` | Runtime-safe schema helpers for workflow tables during development |
| `backend/alembic/versions` | Schema evolution from initial schema through workflow runtime tables |
| `backend/app/runtime` | Provider clients, LLM service, code executor, agent runner, Skill runtime, MCP client, knowledge service, workflow engine |
| `backend/app/runtime/agent_engine` | ReAct agent, LLM wrapper, and tool manager |
| `backend/app/runtime/artifact_skills` | Generic artifact extension point; intentionally empty by default to avoid hard-coded Skill behavior |
| `backend/app/workers` | Celery app and retry task dispatch |
| `backend/app/services/user_file_service.py` | My Files upload/download/delete and generated artifact persistence |
| `frontend/src/router/index.js` | Frontend routes, auth guard, keep-alive route metadata |
| `frontend/src/services/api.js` | Frontend API client and endpoint mapping |
| `frontend/src/views` | Dashboard, login, projects, project detail, workbench, My Files |
| `frontend/src/views/resources` | Resource lists, create/edit forms, Skill detail, Knowledge documents, Workflow detail |
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
| Provider connections | `POST /api/v1/provider-connections/projects/{project_id}/probe-models`, `POST /api/v1/provider-connections/projects/{project_id}/test`, `GET/POST /api/v1/provider-connections/projects/{project_id}`, `GET/PATCH/DELETE /api/v1/provider-connections/{connection_id}`, `POST /api/v1/provider-connections/{connection_id}/test`, `DELETE /api/v1/provider-connections/{connection_id}` |
| Files / My Files | `GET /api/v1/files/me`, `GET /api/v1/files/me/download`, `POST /api/v1/files/me/upload`, `DELETE /api/v1/files/me` |
| Chat/runtime | `GET /api/v1/chat/agents/{agent_id}/debug`, `GET /api/v1/chat/code-execution-audits`, `POST /api/v1/chat/projects/{project_id}/sessions`, `GET /api/v1/chat/projects/{project_id}/sessions`, `GET /api/v1/chat/sessions/{session_id}/messages`, `GET /api/v1/chat/sessions/{session_id}/runs`, `GET /api/v1/chat/runs/{run_id}/events`, `POST /api/v1/chat/sessions/{session_id}/messages` |
| Memory | `POST /api/v1/memory`, `GET /api/v1/memory`, `POST /api/v1/memory/semantic-search`, `POST /api/v1/memory/retry-embeddings` |
| Registry | `POST /api/v1/registry/projects/{project_id}/{kind}`, `GET /api/v1/registry/projects/{project_id}/{kind}`, `GET /api/v1/registry/public/{kind}`, `POST /api/v1/registry/mcp/probe` |
| Knowledge | `POST /api/v1/knowledge/{knowledge_id}/documents/upload`, `GET /api/v1/knowledge/{knowledge_id}/documents`, `DELETE /api/v1/knowledge/{knowledge_id}/documents/{document_id}`, `POST /api/v1/knowledge/{knowledge_id}/reprocess` |
| Skills | `POST /api/v1/skills/{skill_id}/upload`, `POST /api/v1/skills/{skill_id}/upload-folder`, `GET /api/v1/skills/{skill_id}`, `GET /api/v1/skills/{skill_id}/files/content`, `GET /api/v1/skills/projects/{project_id}/skills`, `POST /api/v1/skills/{skill_id}/test`, `POST/PATCH/DELETE/GET /api/v1/skills/agents/{agent_id}/skills`, `GET /api/v1/skills/{skill_id}/agents` |
| Workflows | `POST /api/v1/workflows/{workflow_id}/validate`, `POST /api/v1/workflows/{workflow_id}/run`, `GET /api/v1/workflows/{workflow_id}/runs`, `GET /api/v1/workflows/{workflow_id}/runs/{run_id}` |

## Runtime Capabilities / Runtime 能力

| Capability | Current status |
| --- | --- |
| LLM mode | OpenAI-compatible and localhost provider calls through `llm_service` |
| Provider profile | Env-prefix mapping such as `ZHIPU_*` or `QWEN_*` |
| Provider Connection | Project-level OpenAI-compatible Base URL + API Key, encrypted at rest |
| Code mode | Executes Agent `custom_code` in a restricted subprocess |
| Tool call | code-mode and ReAct paths can call associated Tool resources |
| MCP call | code-mode and ReAct paths can call associated MCP tools |
| Knowledge retrieval | Agents can bind Knowledge resources and retrieve indexed document chunks |
| Skill activation | Bound Skills are discovered by summary and loaded on demand; executable Python entrypoints run through SkillRuntime |
| Skill code runner | Generic runner for uploaded Skill scripts; should not hard-code particular business prompts |
| ReAct engine | Optional `engine_type=react` path with thought/action/observation events |
| Workflow engine | Validates and runs DAG definitions, records run history and per-step trace |
| Runtime timeline | `runtime_runs` and `runtime_run_events` for chat executions |
| Code audits | `GET /api/v1/chat/code-execution-audits` |
| My Files | User uploads and generated artifacts are listed, downloaded, and deleted through `/files/me` |
| Worker | Celery queue for embedding retry with API fallback |

## Database Tables / 数据库表

| Area | Tables |
| --- | --- |
| Auth/projects | `users`, `projects`, `project_members`, `project_member_permissions` |
| Resources | `resources`, `provider_connections` |
| Workflows | `workflow_runs`, `workflow_step_executions` |
| Chat/runtime | `chat_sessions`, `chat_messages`, `runtime_runs`, `runtime_run_events` |
| Memory | `memory_records`, `memory_embedding_jobs` |
| Knowledge | `documents`, `document_chunks`, `agent_knowledge_bindings` |
| Skills | `skill_metadata`, `agent_skill_bindings`, `skill_executions` |

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
| `/resources/<kind>/create`, `/resources/<kind>/:resourceId/edit` | Resource create/edit forms; kind is supplied by route metadata, not user input |
| `/resources/knowledge-bases/:resourceId/documents` | Knowledge document management |
| `/resources/skills/:resourceId/detail` | Skill package upload, file preview, testing, and agent bindings |
| `/workflows`, `/workflows/create`, `/workflows/:resourceId/edit` | Workflow list and visual canvas authoring |
| `/workflows/:resourceId` | Workflow detail, manual test, run history, and step trace |
| `/workbench` | Project chat sessions, agent selection, messages, run timeline/events |
| `/my-files` | Upload, search, paginate, download, and delete user files |

## Known Cleanup Notes / 已知清理说明

See [Maintenance Audit](maintenance-audit.zh-en.md) for the latest redundancy review. In the 2026-07-30 audit, old unused frontend pages and the unused legacy runtime executor wrapper were removed; command entries, migration files, and runtime data directories were kept deliberately.

## Documentation Maintenance Notes / 文档维护建议

1. Keep `mkdocs.yml` as the authoritative navigation list.
2. Keep module docs for user-facing workflows; keep node docs for architecture and implementation design.
3. Do not delete docs that are linked by `mkdocs.yml` unless the nav is updated in the same change.
4. Treat `README.md`, `README.en.md`, and `README.zh.md` as repository landing pages; treat `docs/index.md` as the GitHub Pages landing page.
5. When code changes API paths, update `frontend/src/services/api.js`, this page, and the relevant guide together.
6. When a roadmap item lands in code, move it from `architecture-roadmap` or `design/` into this page and the relevant module guide.