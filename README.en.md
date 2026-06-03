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

## Core APIs

- Project: `POST /api/v1/projects`, `GET /api/v1/projects`
- Resource: `POST /api/v1/resources/projects/{project_id}`
- Chat: `POST /api/v1/chat/projects/{project_id}/sessions`
- Memory: `POST /api/v1/memory`, `POST /api/v1/memory/semantic-search`
- Registry: `POST /api/v1/registry/projects/{project_id}/{kind}`

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
- [docs/quick-start.zh-en.md](docs/quick-start.zh-en.md)
- [docs/testing-playbook.zh-en.md](docs/testing-playbook.zh-en.md)
- [docs/external-resources-integration.zh-en.md](docs/external-resources-integration.zh-en.md)
