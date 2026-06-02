# HyperAgents

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

Set PostgreSQL connection before starting backend:

```bash
set DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hyperagents
```

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
