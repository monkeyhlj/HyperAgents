# Quick Start (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## 1) 先理解这是什么 / What this project is

中文：
HyperAgents 是一个项目优先（Project-first）的 Agent 平台骨架。所有资源都挂在 Project 下，再由 Chat/Runtime 调度执行。

English:
HyperAgents is a project-first Agent platform skeleton. All resources belong to a Project, then are executed through Chat/Runtime.

## 2) 启动顺序 / Startup Order

中文：

1. 启动 PostgreSQL（建议本地 5432）
2. 创建数据库 `hyperagents`
3. 在 backend 执行 Alembic 迁移
4. 启动 backend
5. 启动 frontend

English:

1. Start PostgreSQL (recommended on port 5432)
2. Create database `hyperagents`
3. Run Alembic migrations in backend
4. Start backend
5. Start frontend

补充 / Add-on:

- Runtime Run timeline is produced automatically after Chat message calls.
- Celery worker is optional for basic startup, but recommended for async retry tasks.

## 3) 后端命令 / Backend Commands

```powershell
copy .env.example .env
# 编辑 .env，至少确认 DATABASE_URL 可用

cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade 0001_initial_schema
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

说明 / Notes:

- Runtime Run does not require extra process startup; it is generated in the backend API process.
- Worker queue mode requires Redis + Celery worker process.

## 4) 前端命令 / Frontend Commands

```powershell
cd frontend
npm install
npm run dev
```

## 4.1) Worker（可选但推荐） / Worker (Optional but Recommended)

中文：

- 如果只做本地联调，可以先不启 worker（系统会回退到 API 进程执行重试）。
- 如果要验证 enqueue=true 的排队能力，必须启动 Redis 和 Celery worker。

English:

- For basic local development, worker can be skipped (fallback runs in API process).
- To validate enqueue=true queue mode, Redis and Celery worker must be running.

```powershell
# 1) Ensure .env includes worker settings
# WORKER_ENABLED=true
# WORKER_BROKER_URL=redis://localhost:6379/0
# WORKER_BACKEND_URL=redis://localhost:6379/1

# 2) Start Redis (example, if installed as Windows service)
# redis-server

# 3) Start Celery worker
cd backend
.venv\Scripts\activate
celery -A app.workers.celery_app.celery_app worker -l info
```

## 5) 必要环境变量 / Required Environment Variables

```powershell
# 所有变量统一写入工作区根目录 .env（模板: .env.example）
# Put all variables in workspace-root .env (template: .env.example)

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hyperagents
OPENAI_API_KEY=<your_key>
OPENAI_BASE_URL=
OPENAI_DEFAULT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
LOCALHOST_LLM_BASE_URL=http://localhost:11434/v1
LOCALHOST_DEFAULT_MODEL=qwen2.5:7b
LOCALHOST_EMBEDDING_MODEL=nomic-embed-text
RUNTIME_DEFAULT_PROVIDER=localhost
EMBEDDING_PROVIDER=openai
VITE_API_BASE_URL=http://localhost:8000
WORKER_ENABLED=false
WORKER_BROKER_URL=redis://localhost:6379/0
WORKER_BACKEND_URL=redis://localhost:6379/1

新增 provider 的约定 / Provider profile convention:

- `provider_profile` 作为凭据前缀名，比如 `zhipu`。
- 后端会读取同前缀的环境变量：`ZHIPU_API_KEY`、`ZHIPU_BASE_URL`、`ZHIPU_DEFAULT_MODEL`。
- 如果新增 `claude`，就配置 `CLAUDE_API_KEY`、`CLAUDE_BASE_URL`、`CLAUDE_DEFAULT_MODEL`。

OPENAI_API_KEY
作用：OpenAI 兼容接口的鉴权密钥。
什么时候用：当 provider 走 openai 时必须可用。
怎么配：填真实密钥；不要提交到仓库。

OPENAI_BASE_URL
作用：OpenAI SDK 请求的基础地址。
什么时候用：

官方 OpenAI：可留空（SDK 默认官方地址）
第三方兼容平台（如智谱等）：填平台给的兼容地址
怎么配：你现在填的智谱兼容地址思路是对的。
OPENAI_DEFAULT_MODEL
作用：聊天默认模型名（provider=openai 时生效）。
怎么配：填你目标平台支持的聊天模型名，比如 glm-5.1 或 gpt-4o-mini。

OPENAI_EMBEDDING_MODEL
作用：向量默认模型名（embedding provider=openai 时生效）。
怎么配：必须填“该平台支持的 embedding 模型名”。
注意：text-embedding-3-small 不是所有平台都支持。

LOCALHOST_LLM_BASE_URL
作用：本地模型服务的 OpenAI 兼容地址（通常 Ollama/vLLM 网关）。
怎么配：本地跑 Ollama 常见就是 http://localhost:11434/v1。

LOCALHOST_DEFAULT_MODEL
作用：本地聊天默认模型（provider=localhost 时生效）。
怎么配：填你本地已下载可用的模型名，如 qwen2.5:7b。

LOCALHOST_EMBEDDING_MODEL
作用：本地 embedding 默认模型。
怎么配：填你本地向量模型名，比如 nomic-embed-text。

RUNTIME_DEFAULT_PROVIDER
作用：聊天请求未指定 provider 时，系统默认走哪条通道。
可选：openai 或 localhost。
你当前设为 localhost，表示默认聊天走本地模型。

EMBEDDING_PROVIDER
作用：Memory 自动向量化默认走哪条通道。
可选：openai 或 localhost。
你当前设为 openai，表示向量默认走外部平台。

VITE_API_BASE_URL
作用：前端调用后端 API 的基础地址。
怎么配：本地开发一般 http://localhost:8000；部署后改成线上 API 域名。

WORKER_ENABLED
作用：是否启用队列模式执行 embedding retry。
可选：true 或 false。
怎么配：开发期可先 false；需要验证排队模式时设为 true。

WORKER_BROKER_URL / WORKER_BACKEND_URL
作用：Celery 的 broker/result backend 地址（通常 Redis）。
怎么配：本地无密码 Redis 可用 redis://localhost:6379/0 与 /1；有密码时写成 redis://:password@host:6379/0。

default_resources.json
作用：系统默认资源模板文件，当前用于提供可选的默认 Agent 模板。
位置：backend/app/core/default_resources.json
怎么配：只放模板信息，不放真实密钥；真实凭据仍然从 .env 读取。
约定：模板里可写 provider_profile，例如 zhipu，后端会读取同前缀的 ZHIPU_API_KEY、ZHIPU_BASE_URL、ZHIPU_DEFAULT_MODEL。
```

中文：

- 只用本地模型时，`OPENAI_API_KEY` 可以不设。
- 只用 OpenAI 时，localhost 服务可以不启。
- CORS 白名单可用 `CORS_ALLOW_ORIGINS` 在 `.env` 配置（逗号分隔）。

English:

- If you only use local models, `OPENAI_API_KEY` is optional.
- If you only use OpenAI, local model service is optional.
- Configure CORS whitelist via `CORS_ALLOW_ORIGINS` in `.env` (comma-separated).

## 6) 第一次验证 / First Validation

中文：
访问 `http://localhost:8000/health`，应返回 `{"status":"ok"}`。

English:
Open `http://localhost:8000/health`; expected response is `{"status":"ok"}`.

## 6.0) MCP 本地联调 / MCP Local Validation

中文：

1. 启动 fake MCP server：

```powershell
cd backend
.venv\Scripts\python.exe scripts\mock_mcp_server.py
```

2. 打开前端 `Resources -> MCPs -> Create MCP`
3. 选择 `transport=streamable_http`
4. 填写 `endpoint_url=http://127.0.0.1:8099`
5. 点击 `Test MCP Connection`
6. 保存后在 MCPs 列表页再点行级 `Test`

期望：

- Probe 成功
- Tools 列表至少包含 `ping`、`echo`

English:

1. Start fake MCP server:

```powershell
cd backend
.venv\Scripts\python.exe scripts\mock_mcp_server.py
```

2. Open frontend `Resources -> MCPs -> Create MCP`
3. Set `transport=streamable_http`
4. Fill `endpoint_url=http://127.0.0.1:8099`
5. Click `Test MCP Connection`
6. Save MCP and click row-level `Test` in MCPs list

Expected:

- Probe succeeds
- Tool list contains at least `ping` and `echo`

## 6.1) Runtime Run 验证 / Runtime Run Validation

中文：

1. 注册/登录拿到 access token
2. 创建 project -> 创建 chat session
3. 发送消息到 /api/v1/chat/sessions/{session_id}/messages
4. 查询 /api/v1/chat/sessions/{session_id}/runs
5. 查询 /api/v1/chat/runs/{run_id}/events

期望：

- runs 至少有 1 条新记录
- events 至少包含 runtime running 与 runtime succeeded/failed

English:

1. Register/login and get access token
2. Create project -> create chat session
3. Send message to /api/v1/chat/sessions/{session_id}/messages
4. Query /api/v1/chat/sessions/{session_id}/runs
5. Query /api/v1/chat/runs/{run_id}/events

Expected:

- at least one new run record
- runtime running and runtime succeeded/failed events exist

## 6.2) Worker 排队验证 / Worker Queue Validation

```powershell
curl -X POST "http://localhost:8000/api/v1/memory/retry-embeddings?limit=20&enqueue=true" -H "Authorization: Bearer <access_token>"
```

结果解释 / Result interpretation:

- queued=true: task successfully enqueued, task_id should be non-empty.
- queued=false: worker not enabled/reachable, request falls back to API process execution.

## 6.3) 项目成员权限验证 / Project Membership Permission Validation

中文：

1. owner 创建项目
2. owner 添加普通成员 A（`POST /api/v1/projects/{project_id}/members`）
3. owner 授予 A 添加成员权限（`POST /api/v1/projects/{project_id}/member-managers`）
4. 使用 A 的账号添加成员 B（应成功）
5. 使用 A 的账号删除成员 B（应返回 403）

English:

1. owner creates a project
2. owner adds member A (`POST /api/v1/projects/{project_id}/members`)
3. owner grants A add-member permission (`POST /api/v1/projects/{project_id}/member-managers`)
4. use A to add member B (should succeed)
5. use A to remove member B (should return 403)

说明 / Notes:

- `member_managers` is returned in project payloads.
- Only owner can remove members and revoke delegated permissions.

## 7) 一键启动（按环境） / One-command Startup by Environment

中文：
如果你希望减少手工步骤，可直接使用根目录 `scripts/` 下的脚本。

English:
To reduce manual steps, use scripts in the root `scripts/` folder.

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
