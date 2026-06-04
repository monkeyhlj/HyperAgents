# HyperAgents

<p align="center">
	<strong>A project-first Agent Operating System for teams.</strong><br/>
	Build, orchestrate, and test AI agents with unified runtime, memory, and resource registry.
</p>

<p align="center">
	<a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-red.svg" alt="License"/></a>
	<a href="https://github.com/monkeyhlj"><img src="https://img.shields.io/badge/Author-monkeyhlj-orange.svg" alt="Author"/></a>
	<a href="https://blog.csdn.net/hhhmonkey"><img src="https://img.shields.io/badge/Blog-CSDN-blue.svg" alt="Blog"/></a>
	<a href="https://github.com/monkeyhlj/HyperAgents"><img src="https://img.shields.io/badge/version-0.1.0-brightgreen.svg" alt="Version"/></a>
	<a href="https://github.com/monkeyhlj/HyperAgents/issues"><img src="https://img.shields.io/github/issues/monkeyhlj/HyperAgents" alt="GitHub issues"/></a>
	<a href="https://github.com/monkeyhlj/HyperAgents/pulls"><img src="https://img.shields.io/github/issues-pr/monkeyhlj/HyperAgents" alt="GitHub pull requests"/></a>
	<a href="https://github.com/monkeyhlj/HyperAgents/stargazers"><img src="https://img.shields.io/github/stars/monkeyhlj/HyperAgents.svg?style=social&label=Stars" alt="GitHub stars"/></a>
	<a href="https://github.com/monkeyhlj/HyperAgents/network/members"><img src="https://img.shields.io/github/forks/monkeyhlj/HyperAgents.svg?style=social&label=Forks" alt="GitHub forks"/></a>
</p>

<p align="center">
	<img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python"/>
	<img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI"/>
	<img src="https://img.shields.io/badge/Vue-3.5-42b883?logo=vuedotjs&logoColor=white" alt="Vue"/>
	<img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL"/>
	<img src="https://img.shields.io/badge/pgvector-enabled-4f46e5" alt="pgvector"/>
</p>

<p align="center">
	<a href="README.en.md">English</a>
	·
	<a href="README.zh.md">中文</a>
	·
	<a href="docs/README.md">Docs</a>
</p>

<p align="center">
	Docs Site: <a href="https://monkeyhlj.github.io/HyperAgents/">https://monkeyhlj.github.io/HyperAgents/</a>
</p>

## Why HyperAgents

HyperAgents is designed for teams that want more than a chat demo. It provides a clear project boundary, structured resources, a provider-agnostic runtime, and memory capabilities that can evolve from local development to production-grade deployment.

## Core Capabilities

- Project-first model: all resources belong to a project and follow visibility policies.
- Unified resource system: Agent, Workflow, Tool, Skill, MCP, Knowledge Base.
- Runtime execution layer: route chat requests to OpenAI-compatible or local providers.
- Memory service: write/search memory, auto embedding, retry queue, semantic retrieval.
- Registry APIs: project-scoped registration and cross-project public discovery.
- Full-stack workspace: FastAPI backend and Vue 3 frontend workbench.

## Architecture at a Glance

```mermaid
flowchart LR
		UI[Frontend Workbench\nVue + Vite] --> API[Backend API\nFastAPI]
		API --> Runtime[Runtime Executor]
		Runtime --> LLM1[OpenAI-Compatible Provider]
		Runtime --> LLM2[Local Provider\nOllama/vLLM]
		API --> Memory[Memory Service]
		Memory --> Embed[Embedding Providers]
		API --> DB[(PostgreSQL + pgvector)]
		API --> Registry[Resource Registry\nMCP/Tool/Skill]
```

## Repository Structure

- [backend](backend): FastAPI service, runtime, memory, DB models, Alembic migrations.
- [frontend](frontend): Vue 3 application for project/resource/workbench operations.
- [docs](docs): bilingual node-by-node docs, quick start, and testing playbooks.
- [.env.example](.env.example): centralized environment template.

## Quick Start

1. Copy environment template:

```bash
copy .env.example .env
```

2. Start backend and frontend via scripts:

```bash
./scripts/start-backend.ps1 -Environment dev -RunMigrations
./scripts/start-frontend.ps1 -Environment dev -Install
```

3. Optional but recommended: enable Worker queue mode for async retry tasks.

```bash
# in .env
WORKER_ENABLED=true
WORKER_BROKER_URL=redis://localhost:6379/0
WORKER_BACKEND_URL=redis://localhost:6379/1

# start celery worker
cd backend
.venv\Scripts\activate
celery -A app.workers.celery_app.celery_app worker -l info
```

Notes:

- Runtime Run timeline does not require extra process startup. It is created automatically by chat message execution.
- Worker is required only when you need enqueue=true queue dispatch.
- If worker/redis is unavailable, retry endpoints will fallback to API process execution.

For detailed setup, see:

- [README.en.md](README.en.md)
- [README.zh.md](README.zh.md)
- [docs/guides/quick-start.zh-en.md](docs/guides/quick-start.zh-en.md)
- [docs/guides/runtime-run-worker.zh-en.md](docs/guides/runtime-run-worker.zh-en.md)

## Documentation Index

- [docs/README.md](docs/README.md)
- [docs/guides/testing-playbook.zh-en.md](docs/guides/testing-playbook.zh-en.md)
- [docs/guides/external-resources-integration.zh-en.md](docs/guides/external-resources-integration.zh-en.md)

## Current Status

HyperAgents is under active iteration. APIs and docs are evolving toward a stable v1 workflow for project operations, provider integration, and memory reliability.
