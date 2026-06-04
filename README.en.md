# HyperAgents (English)

Language: [中文](README.zh.md) | [Landing](README.md) | [Docs](docs/README.md)

HyperAgents is a project-first Agent Operating System for teams that want structured AI workflows, not single-page demos.

## Highlights

- Project-first resource model with built-in visibility boundaries.
- Unified resource types: Agent, Workflow, Tool, Skill, MCP, Knowledge Base.
- Provider-agnostic runtime (OpenAI-compatible and local model gateways).
- Memory service with automatic embedding, retry queue, and hybrid retrieval.
- Registry APIs for project-scoped and public MCP/Tool/Skill discovery.
- Full-stack workspace: FastAPI backend + Vue 3 frontend workbench.

## Monorepo Layout

- `backend`: API layer, runtime executor, memory service, SQLAlchemy models, Alembic migrations.
- `frontend`: Vue + Vite app for projects/resources/workbench testing.
- `docs`: bilingual architecture nodes, playbooks, and integration guides.
- `scripts`: environment-aware startup scripts for Windows and Linux.

## Quick Start

### 1) Prepare environment

```bash
copy .env.example .env
```

Minimum required values in `.env`:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hyperagents
VITE_API_BASE_URL=http://localhost:8000
```

### 2) Start services (recommended)

Windows PowerShell:

```powershell
./scripts/start-backend.ps1 -Environment dev -RunMigrations
./scripts/start-frontend.ps1 -Environment dev -Install
```

Linux/macOS Bash:

```bash
./scripts/start-backend.sh --env dev --migrate
./scripts/start-frontend.sh --env dev --install
```

Service URLs:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## Runtime and Provider Configuration

Supported runtime providers:

- `openai`
- `localhost` (aliases: `ollama`, `vllm`)

Common environment keys:

```bash
OPENAI_API_KEY=<your_key>
OPENAI_BASE_URL=
OPENAI_DEFAULT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
LOCALHOST_LLM_BASE_URL=http://localhost:11434/v1
LOCALHOST_DEFAULT_MODEL=qwen2.5:7b
LOCALHOST_EMBEDDING_MODEL=nomic-embed-text
RUNTIME_DEFAULT_PROVIDER=localhost
EMBEDDING_PROVIDER=openai
```

Notes:

- `RUNTIME_DEFAULT_PROVIDER` controls default chat generation route.
- `EMBEDDING_PROVIDER` controls default memory embedding route.
- `OPENAI_EMBEDDING_MODEL` must be valid for your configured provider endpoint.

Provider profile convention:

- `provider_profile` is the credential prefix, for example `zhipu`.
- The backend reads matching env vars with the same prefix: `ZHIPU_API_KEY`, `ZHIPU_BASE_URL`, `ZHIPU_DEFAULT_MODEL`.
- To add `claude`, configure `CLAUDE_API_KEY`, `CLAUDE_BASE_URL`, and `CLAUDE_DEFAULT_MODEL`.

## Runtime Run and Worker

Runtime Run (runs + events) records execution timeline for each chat request. It is generated automatically by chat message execution and does not require a separate runtime process.

Worker mode (Celery + Redis) is used for async embedding retry dispatch and is optional:

- For local development, worker can be skipped (fallback runs in API process).
- To validate queue mode (`enqueue=true`), Redis and Celery worker must be running.

Recommended worker settings:

```bash
WORKER_ENABLED=true
WORKER_BROKER_URL=redis://localhost:6379/0
WORKER_BACKEND_URL=redis://localhost:6379/1
```

Start worker:

```bash
cd backend
.venv\Scripts\activate
celery -A app.workers.celery_app.celery_app worker -l info
```

Quick validation:

1. Send message via `POST /api/v1/chat/sessions/{session_id}/messages`
2. Query runs via `GET /api/v1/chat/sessions/{session_id}/runs`
3. Query events via `GET /api/v1/chat/runs/{run_id}/events`
4. Trigger queue retry via `POST /api/v1/memory/retry-embeddings?limit=20&enqueue=true`

Result interpretation:

- `queued=true`: task enqueued successfully and `task_id` is present.
- `queued=false`: queue unavailable, request fallback executed in API process.

## Core APIs

- Project: `POST /api/v1/projects`, `GET /api/v1/projects`
- Project update/delete: `PATCH /api/v1/projects/{project_id}`, `DELETE /api/v1/projects/{project_id}`
- Project members: `POST /api/v1/projects/{project_id}/members`, `DELETE /api/v1/projects/{project_id}/members/{member_id}`
- Project member managers: `POST /api/v1/projects/{project_id}/member-managers`, `DELETE /api/v1/projects/{project_id}/member-managers/{member_id}`
- Resource: `POST /api/v1/resources/projects/{project_id}`
- Chat: `POST /api/v1/chat/projects/{project_id}/sessions`
- Memory: `POST /api/v1/memory`, `POST /api/v1/memory/semantic-search`
- Registry: `POST /api/v1/registry/projects/{project_id}/{kind}`

Membership rule summary:

- owner can add/remove members.
- delegated member manager can add members, but cannot remove members.

## Memory V1 Snapshot

- Scope/type values: `conversation`, `project`, `agent`, `execution`, `global`
- Visibility: `private`, `project`, `public`
- Embedding status: `skipped`, `pending`, `succeeded`, `failed`

Hybrid ranking:

- `hybrid_score = similarity_weight * similarity_score + (1 - similarity_weight) * importance_score`

## Database and Migrations

```bash
cd backend
alembic upgrade head
```

Generate migration:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
```

## Documentation

- [docs/README.md](docs/README.md)
- [docs/guides/quick-start.zh-en.md](docs/guides/quick-start.zh-en.md)
- [docs/guides/testing-playbook.zh-en.md](docs/guides/testing-playbook.zh-en.md)
- [docs/guides/external-resources-integration.zh-en.md](docs/guides/external-resources-integration.zh-en.md)
