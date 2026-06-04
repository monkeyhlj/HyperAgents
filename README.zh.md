# HyperAgents (中文)

语言: [English](README.en.md) | [主页](README.md) | [文档](docs/README.md)

HyperAgents 是一个面向团队的 Project-first Agent Operating System，适合构建可管理、可扩展、可验证的 AI Agent 平台能力。

## 核心亮点

- 项目优先模型，天然具备资源边界与可见性策略。
- 统一资源体系：Agent、Workflow、Tool、Skill、MCP、Knowledge Base。
- Provider 无关 Runtime，支持 OpenAI 兼容和本地模型网关。
- Memory 服务支持自动向量化、失败重试队列与混合检索。
- Registry API 支持项目内注册与跨项目公开发现。
- 全栈工作区：FastAPI 后端 + Vue 3 前端工作台。

## 仓库结构

- `backend`：API、Runtime、Memory、数据库模型与 Alembic 迁移。
- `frontend`：项目管理、资源管理与 Workbench 对话界面。
- `docs`：双语节点文档、测试手册、外部集成指南。
- `scripts`：支持 dev/staging/prod 的启动脚本（Windows + Linux）。

## 快速开始

### 1) 准备环境文件

```bash
copy .env.example .env
```

`.env` 最低建议配置：

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hyperagents
VITE_API_BASE_URL=http://localhost:8000
```

### 2) 启动后端和前端（推荐）

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

服务地址：

- 后端: `http://localhost:8000`
- 前端: `http://localhost:5173`

## Runtime 与 Provider 配置

支持的 Runtime Provider：

- `openai`
- `localhost`（别名：`ollama`、`vllm`）

常用环境变量：

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

说明：

- `RUNTIME_DEFAULT_PROVIDER` 决定默认聊天走哪条模型通道。
- `EMBEDDING_PROVIDER` 决定 Memory 默认向量化走哪条通道。
- `OPENAI_EMBEDDING_MODEL` 必须是你当前 `OPENAI_BASE_URL` 对应供应商支持的向量模型名。

新增 provider 的约定：

- `provider_profile` 作为凭据前缀名，比如 `zhipu`。
- 后端会读取同前缀的环境变量：`ZHIPU_API_KEY`、`ZHIPU_BASE_URL`、`ZHIPU_DEFAULT_MODEL`。
- 如果要新增 `claude`，就配置 `CLAUDE_API_KEY`、`CLAUDE_BASE_URL`、`CLAUDE_DEFAULT_MODEL`。

## Runtime Run 与 Worker

Runtime Run（runs + events）用于记录一次对话执行的时间线，发起聊天消息后会自动写入，无需单独启动 Runtime 进程。

Worker（Celery + Redis）用于异步执行 embedding retry，属于可选能力：

- 本地联调可先不开 worker，系统会回退到 API 进程执行。
- 需要验证排队模式（`enqueue=true`）时，必须启用 worker 与 Redis。

建议配置：

```bash
WORKER_ENABLED=true
WORKER_BROKER_URL=redis://localhost:6379/0
WORKER_BACKEND_URL=redis://localhost:6379/1
```

启动 worker：

```bash
cd backend
.venv\Scripts\activate
celery -A app.workers.celery_app.celery_app worker -l info
```

快速验收：

1. 发送消息到 `POST /api/v1/chat/sessions/{session_id}/messages`
2. 查询 `GET /api/v1/chat/sessions/{session_id}/runs`
3. 查询 `GET /api/v1/chat/runs/{run_id}/events`
4. 调用 `POST /api/v1/memory/retry-embeddings?limit=20&enqueue=true`

返回解释：

- `queued=true`: 已成功入队，`task_id` 非空。
- `queued=false`: 队列不可用，已自动回退到 API 进程执行。

## 核心 API 概览

- Project: `POST /api/v1/projects`, `GET /api/v1/projects`
- Project 更新/删除: `PATCH /api/v1/projects/{project_id}`, `DELETE /api/v1/projects/{project_id}`
- Project 成员: `POST /api/v1/projects/{project_id}/members`, `DELETE /api/v1/projects/{project_id}/members/{member_id}`
- Project 成员管理授权: `POST /api/v1/projects/{project_id}/member-managers`, `DELETE /api/v1/projects/{project_id}/member-managers/{member_id}`
- Resource: `POST /api/v1/resources/projects/{project_id}`
- Chat: `POST /api/v1/chat/projects/{project_id}/sessions`
- Memory: `POST /api/v1/memory`, `POST /api/v1/memory/semantic-search`
- Registry: `POST /api/v1/registry/projects/{project_id}/{kind}`

成员权限规则：

- owner 可以添加和移除成员。
- 被委托成员（member manager）可以添加成员，但不能移除成员。

## Memory V1 摘要

- scope/type: `conversation`, `project`, `agent`, `execution`, `global`
- visibility: `private`, `project`, `public`
- embedding_status: `skipped`, `pending`, `succeeded`, `failed`

混合评分公式：

- `hybrid_score = similarity_weight * similarity_score + (1 - similarity_weight) * importance_score`

## 数据库与迁移

```bash
cd backend
alembic upgrade head
```

创建迁移：

```bash
cd backend
alembic revision --autogenerate -m "describe change"
```

## 文档入口

- [docs/README.md](docs/README.md)
- [docs/guides/quick-start.zh-en.md](docs/guides/quick-start.zh-en.md)
- [docs/guides/testing-playbook.zh-en.md](docs/guides/testing-playbook.zh-en.md)
- [docs/guides/external-resources-integration.zh-en.md](docs/guides/external-resources-integration.zh-en.md)
