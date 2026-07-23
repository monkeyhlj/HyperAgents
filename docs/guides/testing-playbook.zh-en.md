# Testing Playbook (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [代码与 API 对齐](../reference/code-api-map.zh-en.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## A. 最小可用测试 / Minimum Viable Test

### Step 1: 启动依赖 / Start dependencies

启动 PostgreSQL，创建 `hyperagents` 数据库。若要验证 queue mode，再启动 Redis。

Start PostgreSQL and create the `hyperagents` database. Start Redis only when validating queue mode.

### Step 2: 迁移数据库 / Run migrations

```powershell
copy .env.example .env
# 编辑 .env 并确认 DATABASE_URL

cd backend
.venv\Scripts\activate
alembic upgrade head
```

说明 / Notes:

- 最新迁移包含 users、runtime_runs/runtime_run_events、provider_connections。
- 若未迁移到 head，Workbench Timeline、Provider Connection 等能力会报表不存在。

### Step 3: 启动后端 / Start backend

```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

### Step 4: 健康检查 / Health check

```powershell
$API_BASE_URL = "http://localhost:8000"
curl "$API_BASE_URL/health"
```

Expected: `{"status":"ok"}`

## B. API E2E 测试顺序 / API E2E Sequence

### 0) Register or login

```powershell
$API_BASE_URL = "http://localhost:8000"
curl -X POST "$API_BASE_URL/api/v1/auth/register" -H "Content-Type: application/json" -d '{"username":"demo","password":"secret123","display_name":"Demo User"}'
```

若已注册，使用登录接口：

```powershell
curl -X POST "$API_BASE_URL/api/v1/auth/login" -H "Content-Type: application/json" -d '{"account":"demo","password":"secret123"}'
```

后续请求统一带：`Authorization: Bearer <access_token>`。

### 1) Create project

```powershell
curl -X POST "$API_BASE_URL/api/v1/projects" -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"name":"Demo","description":"for test"}'
```

记录返回的 `project_id`。

### 2) Add agent resource

```powershell
curl -X POST "$API_BASE_URL/api/v1/resources/projects/{project_id}" -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"kind":"agent","name":"agent-openai","visibility":"project","model_provider":"openai","model_name":"gpt-4o-mini","config":{"system_prompt":"You are a helpful network assistant."}}'
```

记录返回的 `agent_id`。

### 3) Provider Connection probe/test

```powershell
curl -X POST "$API_BASE_URL/api/v1/provider-connections/projects/{project_id}/probe-models" -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"provider_type":"openai_compatible","base_url":"https://api.openai.com/v1","api_key":"<api_key>"}'
```

```powershell
curl -X POST "$API_BASE_URL/api/v1/provider-connections/projects/{project_id}/test" -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"provider_type":"openai_compatible","base_url":"https://api.openai.com/v1","api_key":"<api_key>","model_name":"gpt-4o-mini","text":"ping"}'
```

### 4) Create chat session and send message

```powershell
curl -X POST "$API_BASE_URL/api/v1/chat/projects/{project_id}/sessions" -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"title":"session-1"}'
```

```powershell
curl -X POST "$API_BASE_URL/api/v1/chat/sessions/{session_id}/messages" -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"text":"analyze cpu usage trend","agent_id":"{agent_id}"}'
```

响应应包含 `run_id`，并可能包含 `used_tools` / `used_mcps`。

### 5) Runtime timeline

```powershell
curl "$API_BASE_URL/api/v1/chat/projects/{project_id}/sessions" -H "Authorization: Bearer <access_token>"
curl "$API_BASE_URL/api/v1/chat/sessions/{session_id}/messages" -H "Authorization: Bearer <access_token>"
curl "$API_BASE_URL/api/v1/chat/sessions/{session_id}/runs" -H "Authorization: Bearer <access_token>"
curl "$API_BASE_URL/api/v1/chat/runs/{run_id}/events" -H "Authorization: Bearer <access_token>"
```

### 6) Project member permissions

```powershell
curl -X POST "$API_BASE_URL/api/v1/projects/{project_id}/members" -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"user_id":"member-a"}'
curl -X POST "$API_BASE_URL/api/v1/projects/{project_id}/member-managers" -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"member_id":"member-a"}'
curl -X DELETE "$API_BASE_URL/api/v1/projects/{project_id}/members/member-a" -H "Authorization: Bearer <access_token>"
```

### 7) MCP probe

先启动 mock MCP server：

```powershell
cd backend
.venv\Scripts\python.exe scripts\mock_mcp_server.py
```

再调用 probe：

```powershell
curl -X POST "$API_BASE_URL/api/v1/registry/mcp/probe" -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"project_id":"{project_id}","config":{"transport":"streamable_http","endpoint_url":"http://127.0.0.1:8099","timeout_seconds":8}}'
```

### 8) Memory write/search/retry

```powershell
curl -X POST "$API_BASE_URL/api/v1/memory" -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"memory_scope":"project","memory_type":"project","project_id":"{project_id}","visibility":"project","importance_score":0.9,"content":{"core_switch":"10.1.1.1","window":"Sat 02:00"},"auto_embedding":false}'
```

普通查询：

```powershell
curl "$API_BASE_URL/api/v1/memory?project_id={project_id}&memory_scope=project&memory_type=project" -H "Authorization: Bearer <access_token>"
```

语义检索需要 `query_embedding` 维度与 `MEMORY_EMBEDDING_DIMENSIONS` 一致，默认是 1536。不要用 3 维示例向量直接测试默认库。

重试：

```powershell
curl -X POST "$API_BASE_URL/api/v1/memory/retry-embeddings?limit=20" -H "Authorization: Bearer <access_token>"
curl -X POST "$API_BASE_URL/api/v1/memory/retry-embeddings?limit=20&enqueue=true" -H "Authorization: Bearer <access_token>"
```

### 9) Code execution audit

当 code-mode Agent 执行后，可查询：

```powershell
curl "$API_BASE_URL/api/v1/chat/code-execution-audits?project_id={project_id}&limit=20" -H "Authorization: Bearer <access_token>"
```

## C. 前端手工测试 / Frontend Manual Test

1. 确认 `.env` 中 `VITE_API_BASE_URL` 指向后端地址。
2. 访问 `http://localhost:5173`。
3. 在 Login 页面注册或登录。
4. Projects 页面创建项目，并在成员管理弹窗中添加/移除成员、授权 member manager。
5. Resources 页面创建 Agent/Tool/Skill/MCP/Knowledge Base/Workflow。
6. Agent 页面测试 Env profile 和 URL + API Key Provider Connection。
7. MCP 页面测试 Quick Test 和行级 Test。
8. Workbench 页面创建 session、加载历史 session、发送消息、查看 run/events 和 Tool/MCP 标签。
9. 观察 backend 日志和 API 返回。

## D. 常见失败排查 / Common Troubleshooting

- `401 Invalid token`: 未登录或 Authorization 头缺失/过期。
- `403 No access to project`: 当前用户不是项目 owner/member。
- `relation "runtime_runs" does not exist`: 未执行最新 Alembic 迁移。
- `relation "provider_connections" does not exist`: 未迁移到 `0006_provider_connections` 或 `head`。
- `embedding generation failed`: provider 配置错误或模型服务不可达。
- `query_embedding dimension must be ...`: 向量维度不匹配。
- `vector extension` error: PostgreSQL 未安装/启用 pgvector。
- `enqueue=true but queued=false`: Worker 未启用或 Redis/Celery 不可用，系统已回退到 API 进程执行。
- Provider Connection 测试失败：检查 Base URL、API Key、模型名、`PROVIDER_CONNECTION_SECRET_KEY`。
- MCP probe 失败：检查 endpoint、headers、timeout、mock server 是否启动。
