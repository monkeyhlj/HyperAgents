# HyperAgents (English)

Language switch: [中文](README.zh.md) | [Entry](README.md)

HyperAgents is an Agent Operating System style platform for teams to build, run, and test AI agents.

## V1 Scope

- Project-first model (all resources belong to a project)
- Resource management for:
  - Agent
  - Workflow
  - Tool
  - Skill
  - MCP Server
  - Knowledge Base
- Visibility policy per resource:
  - `private` (owner only)
  - `project` (project members)
  - `public` (everyone)
- Project chat workbench for testing configured resources
- Dual-mode direction:
  - visual management (web UI)
  - code-first extensibility (backend runtime abstractions)

## Monorepo Structure

- `backend`: FastAPI service (API + runtime skeleton)
- `frontend`: Vue 3 + Vite web application

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Create workspace environment file before starting backend:

```bash
copy .env.example .env
```

Then edit `.env` and at least set:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hyperagents
```

Optional local bootstrap behavior:

```bash
AUTO_CREATE_TABLES=true
```

By default, table creation is expected through Alembic migrations.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`, backend on `http://localhost:8000`.

## Next Milestones

- Persist to PostgreSQL + pgvector
- Add Redis job queue and runtime workers
- Integrate real model providers (OpenAI, local vLLM/Ollama)
- Integrate MCP transport/auth
- Add execution sandbox (Docker / Firecracker)
- Add RBAC and org-level collaboration

## Memory Service V1

Memory is now a platform-level service with explicit scope and visibility.

Supported scope and type values:

- `conversation`
- `project`
- `agent`
- `execution`
- `global`

Visibility values:

- `private`
- `project`
- `public`

API:

- `POST /api/v1/memory` store memory
- `GET /api/v1/memory` search memory with filters
- `POST /api/v1/memory/semantic-search` hybrid retrieval (vector similarity + importance)
- `POST /api/v1/memory/retry-embeddings` process pending embedding retry jobs

Core fields:

- `project_id`, `agent_id`, `session_id`, `workflow_run_id`
- `importance_score` (0~1)
- `content` (JSON)
- `embedding_status` (`skipped` / `pending` / `succeeded` / `failed`)
- `embedding`, `embedding_provider`, `embedding_model`, `embedding_error`

### Semantic Search Request Example

```json
{
  "query_embedding": [0.01, 0.02, 0.03],
  "top_k": 10,
  "project_id": "<project_id>",
  "memory_scope": "project",
  "memory_type": "project",
  "min_importance": 0.3,
  "similarity_weight": 0.7
}
```

`query_embedding` and stored `embedding` dimensions must match `MEMORY_EMBEDDING_DIMENSIONS` (default 1536).

Result score uses hybrid ranking:

- `hybrid_score = similarity_weight * similarity_score + (1 - similarity_weight) * importance_score`

## Alembic Migrations

Migration files are under `backend/alembic`.

Run migrations:

```bash
cd backend
alembic upgrade head
```

Create a new migration after schema changes:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
```

## LLM Provider Adapter

Runtime now supports unified provider routing via Agent resource configuration.

Supported provider names:

- `openai`
- `localhost` (also aliases: `ollama`, `vllm`)

Environment variables are now centrally managed in workspace `.env` (template: `.env.example`).

Main LLM-related keys:

```bash
OPENAI_API_KEY=<your_key>
OPENAI_BASE_URL=
OPENAI_DEFAULT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
LOCALHOST_LLM_BASE_URL=http://localhost:11434/v1
LOCALHOST_DEFAULT_MODEL=qwen2.5:7b
LOCALHOST_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_PROVIDER=openai
```

When sending chat with `agent_id`, runtime reads that Agent resource's `model_provider`, `model_name`, and `config.system_prompt`.

## Automatic Memory Embedding

Memory write now supports server-side embedding generation, so clients do not need to pass vectors.

`POST /api/v1/memory` payload fields:

- `auto_embedding` (default `true`)
- `retry_on_embedding_failure` (default `true`)
- `embedding_provider` (optional override, `openai` / `localhost`)
- `embedding_model` (optional override)
- `embedding_input` (optional custom text; defaults to normalized JSON content)

When `auto_embedding=true`, backend generates and stores vector automatically.

If embedding generation fails:

- memory write still succeeds
- `embedding_status` is set to `failed`
- retry job is enqueued
- backend triggers one asynchronous retry pass after response

You can also run retries in batch via:

- `POST /api/v1/memory/retry-embeddings?limit=20`

## Registry APIs (MCP / Tool / Skill)

Project-scoped registry creation:

- `POST /api/v1/registry/projects/{project_id}/mcp`
- `POST /api/v1/registry/projects/{project_id}/tool`
- `POST /api/v1/registry/projects/{project_id}/skill`

Project registry listing with visibility filter:

- `GET /api/v1/registry/projects/{project_id}/mcp?visibility=project`
- `GET /api/v1/registry/projects/{project_id}/tool?visibility=private`
- `GET /api/v1/registry/projects/{project_id}/skill?visibility=public`

Public registry listing across projects:

- `GET /api/v1/registry/public/mcp`
- `GET /api/v1/registry/public/tool`
- `GET /api/v1/registry/public/skill`
