# HyperAgents (English)

Language: [Landing](README.md) | [中文](README.zh.md) | [Docs](docs/README.md) | [Docs Site](https://monkeyhlj.github.io/HyperAgents/)

HyperAgents is a project-first Agent Operating System prototype for teams that need structured AI workflows rather than isolated chat demos.

## Highlights

- Project-first domain model with project/private/public resource visibility.
- Unified resource registry for Agents, Tools, Skills, MCPs, Knowledge Bases, and Workflows.
- Agent Workbench for persisted chat sessions, runtime traces, bound capabilities, and generated files.
- Skill runtime with uploaded Skill packages, progressive-disclosure instructions, and script-aware execution paths.
- Knowledge base management with document upload, retrieval configuration, and agent binding.
- Visual Workflow builder with graph nodes, branching, JSON synchronization, test runs, and run history.
- My Files workspace for uploaded inputs and generated artifacts.
- Provider profiles and project-level Provider Connections for OpenAI-compatible endpoints.
- Optional worker queue mode for async retry tasks.

## Monorepo Layout

- `backend`: FastAPI API, runtime, skill/workflow execution, SQLAlchemy models, Alembic migrations.
- `frontend`: Vue + Vite app for dashboard, projects, resources, workbench, workflows, and files.
- `docs`: bilingual documentation site source, module guides, design notes, and operations references.
- `scripts`: environment-aware startup scripts for Windows and Linux/macOS.
- `.env.example`: workspace-root environment template.

## Quick Start

### 1. Prepare Environment

```powershell
copy .env.example .env
```

Minimum local values:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hyperagents
VITE_API_BASE_URL=http://localhost:8000
```

### 2. Start Services

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
- API docs: `http://localhost:8000/docs`

## Runtime And Providers

HyperAgents uses OpenAI-compatible provider profiles. A profile name maps to environment variable prefixes:

```bash
NVIDIA_API_KEY=<your_key>
NVIDIA_BASE_URL=<compatible_endpoint>
NVIDIA_DEFAULT_MODEL=<model_name>

OPENAI_API_KEY=<your_key>
OPENAI_BASE_URL=
OPENAI_DEFAULT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

`provider_profile=nvidia` makes the backend read `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, and `NVIDIA_DEFAULT_MODEL`. Project-level Provider Connections can also store encrypted endpoint credentials in the database.

## Worker Mode

Runtime run timelines are created automatically by chat and workflow execution. A separate process is not required for normal local testing.

Worker mode is optional and used for queue-backed async tasks:

```bash
WORKER_ENABLED=true
WORKER_BROKER_URL=redis://localhost:6379/0
WORKER_BACKEND_URL=redis://localhost:6379/1
```

Start worker:

```powershell
cd backend
.venv\Scripts\activate
celery -A app.workers.celery_app.celery_app worker -l info
```

If Redis/worker is unavailable, supported retry endpoints fall back to API-process execution.

## Key Areas To Try

1. Create a project and add members.
2. Create or import Agents, Tools, Skills, MCPs, and Knowledge Bases.
3. Bind Skills and Knowledge Bases to an Agent.
4. Test the Agent in Workbench and inspect runtime traces.
5. Upload files in My Files and generate artifacts through Skills.
6. Build a Workflow visually, test it, and review run history.

## Documentation

- [docs/README.md](docs/README.md)
- [docs/guides/quick-start.zh-en.md](docs/guides/quick-start.zh-en.md)
- [docs/guides/frontend-guide.zh-en.md](docs/guides/frontend-guide.zh-en.md)
- [docs/modules/resources.zh-en.md](docs/modules/resources.zh-en.md)
- [docs/modules/workflows.zh-en.md](docs/modules/workflows.zh-en.md)
- [docs/reference/code-api-map.zh-en.md](docs/reference/code-api-map.zh-en.md)

## Status

HyperAgents is under active iteration. The current focus is improving general-purpose Skill execution quality, workflow orchestration ergonomics, and documentation clarity for first-time users.
