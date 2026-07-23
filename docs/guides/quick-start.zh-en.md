# Quick Start (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [代码与 API 对齐](../reference/code-api-map.zh-en.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## 1) 这是什么 / What this project is

HyperAgents 是一个项目优先（Project-first）的 Agent 平台骨架。资源归属于 Project，再由 Chat/Runtime 调度执行；前端提供 Projects、Resources、Workbench 等操作入口。

HyperAgents is a project-first Agent platform skeleton. Resources belong to Projects and are executed through Chat/Runtime; the frontend provides Projects, Resources, and Workbench workflows.

## 2) 启动顺序 / Startup Order

1. 启动 PostgreSQL，并创建 `hyperagents` 数据库。
2. 从 `.env.example` 复制根目录 `.env`，确认 `DATABASE_URL`。
3. 在 backend 执行 `alembic upgrade head`。
4. 启动 backend。
5. 启动 frontend。
6. 可选：启动 Redis + Celery worker 验证 queue mode。

## 3) 后端命令 / Backend Commands

```powershell
copy .env.example .env
# 编辑 .env，至少确认 DATABASE_URL 可用

cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

说明 / Notes:

- Runtime Run timeline 由 Chat API 自动生成，不需要单独进程。
- Worker 只在验证 `enqueue=true` 或生产异步任务时需要。

## 4) 前端命令 / Frontend Commands

```powershell
cd frontend
npm install
npm run dev
```

默认地址 / Defaults:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## 5) Worker（可选） / Worker (Optional)

```dotenv
WORKER_ENABLED=true
WORKER_BROKER_URL=redis://localhost:6379/0
WORKER_BACKEND_URL=redis://localhost:6379/1
```

```powershell
cd backend
.venv\Scripts\activate
celery -A app.workers.celery_app.celery_app worker -l info
```

- 本地联调可不启 worker，系统会回退到 API 进程执行 retry。
- 验证 `retry-embeddings?enqueue=true` 时需要 Redis + Celery worker。

## 6) 核心环境变量 / Core Environment Variables

基础配置：

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hyperagents
AUTO_CREATE_TABLES=false
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
VITE_API_BASE_URL=http://localhost:8000
AUTH_SECRET_KEY=change-me
PROVIDER_CONNECTION_SECRET_KEY=change-me-too
```

模型配置：

```dotenv
OPENAI_API_KEY=<your_key>
OPENAI_BASE_URL=
OPENAI_DEFAULT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
LOCALHOST_LLM_BASE_URL=http://localhost:11434/v1
LOCALHOST_DEFAULT_MODEL=qwen2.5:7b
LOCALHOST_EMBEDDING_MODEL=nomic-embed-text
RUNTIME_DEFAULT_PROVIDER=localhost
EMBEDDING_PROVIDER=openai
MEMORY_EMBEDDING_DIMENSIONS=1536
MODEL_REQUEST_TIMEOUT_SECONDS=60
```

代码执行与 worker：

```dotenv
CODE_EXECUTION_TIMEOUT_SECONDS=5
CODE_EXECUTION_MAX_OUTPUT_CHARS=8000
WORKER_ENABLED=false
WORKER_BROKER_URL=redis://localhost:6379/0
WORKER_BACKEND_URL=redis://localhost:6379/1
```

Provider profile 约定：

- `provider_profile=zhipu` 会读取 `ZHIPU_API_KEY`、`ZHIPU_BASE_URL`、`ZHIPU_DEFAULT_MODEL`。
- 项目级 URL + API Key 模型连接优先使用 Provider Connection；API Key 会加密保存到数据库。
- 只用本地模型时，`OPENAI_API_KEY` 可不设；只用 OpenAI 时，localhost 服务可不启。

## 7) 第一次验证 / First Validation

```powershell
curl http://localhost:8000/health
```

预期 / Expected:

```json
{"status":"ok"}
```

## 8) Provider Connection 自测 / Provider Connection Validation

1. 打开 `Resources -> Agents -> Create Agent`。
2. 在 `Custom model settings` 选择 `URL + API Key`。
3. 填写 OpenAI-compatible Base URL 与 API Key。
4. 点击 `Load Models` 获取模型列表。
5. 选择模型并点击 `Test`。
6. 点击 `Save Connection`，Agent 会保存 `provider_connection_id`。

生产环境请设置稳定的 `PROVIDER_CONNECTION_SECRET_KEY`，避免使用默认开发密钥。

## 9) MCP 本地联调 / MCP Local Validation

```powershell
cd backend
.venv\Scripts\python.exe scripts\mock_mcp_server.py
```

然后在前端：

1. 打开 `Resources -> MCPs -> Create MCP`。
2. 选择 `transport=streamable_http`。
3. 填写 `endpoint_url=http://127.0.0.1:8099`。
4. 点击 `Test MCP Connection`。
5. 保存后在 MCPs 列表页再点行级 `Test`。

期望：Probe 成功，Tools 至少包含 `ping`、`echo`。

## 10) Runtime Run 验证 / Runtime Run Validation

1. 注册/登录拿到 access token。
2. 创建 project。
3. 创建 agent。
4. 创建 chat session。
5. 发送消息到 `/api/v1/chat/sessions/{session_id}/messages`。
6. 查询 `/api/v1/chat/sessions/{session_id}/runs`。
7. 查询 `/api/v1/chat/runs/{run_id}/events`。

期望：runs 至少有一条新记录，events 至少包含 runtime running 与 runtime succeeded/failed。

## 11) Worker 排队验证 / Worker Queue Validation

```powershell
curl -X POST "http://localhost:8000/api/v1/memory/retry-embeddings?limit=20&enqueue=true" -H "Authorization: Bearer <access_token>"
```

- `queued=true`: 任务已进入 Celery。
- `queued=false`: worker 未启用或不可达，已回退到 API 进程执行。

## 12) 一键启动脚本 / Startup Scripts

PowerShell:

```powershell
./scripts/start-backend.ps1 -Environment dev -RunMigrations
./scripts/start-frontend.ps1 -Environment dev -Install
```

Bash:

```bash
./scripts/start-backend.sh --env dev --migrate
./scripts/start-frontend.sh --env dev --install
```
