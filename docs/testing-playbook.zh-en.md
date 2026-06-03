# Testing Playbook (中文 + English)

导航 / Navigation: [返回项目首页](../README.md) | [文档首页](README.md) | [中文 README](../README.zh.md) | [English README](../README.en.md)

## A. 最小可用测试 / Minimum Viable Test

### Step 1: 启动依赖 / Start dependencies

中文：启动 PostgreSQL，创建 `hyperagents` 数据库。
English: Start PostgreSQL and create `hyperagents` database.

### Step 2: 迁移数据库 / Run migrations

```powershell
copy .env.example .env
# 编辑 .env 并确认 DATABASE_URL

cd backend
.venv\Scripts\activate
alembic upgrade head
```

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

### 1) Create project

```powershell
curl -X POST "$API_BASE_URL/api/v1/projects" -H "Content-Type: application/json" -H "x-user-id: demo-user" -d '{"name":"Demo","description":"for test"}'
```

记录返回的 `project_id`。
Store the returned `project_id`.

### 2) Add agent resource

```powershell
curl -X POST "$API_BASE_URL/api/v1/resources/projects/{project_id}" -H "Content-Type: application/json" -H "x-user-id: demo-user" -d '{"kind":"agent","name":"agent-openai","visibility":"project","model_provider":"openai","model_name":"gpt-4o-mini","config":{"system_prompt":"You are a helpful network assistant."}}'
```

记录返回 `agent_id`。
Store returned `agent_id`.

### 3) Create chat session

```powershell
curl -X POST "$API_BASE_URL/api/v1/chat/projects/{project_id}/sessions" -H "Content-Type: application/json" -H "x-user-id: demo-user" -d '{"title":"session-1"}'
```

记录返回 `session_id`。
Store returned `session_id`.

### 4) Send message via agent

```powershell
curl -X POST "$API_BASE_URL/api/v1/chat/sessions/{session_id}/messages" -H "Content-Type: application/json" -H "x-user-id: demo-user" -d '{"text":"analyze cpu usage trend","agent_id":"{agent_id}"}'
```

### 5) Write memory with auto embedding

```powershell
curl -X POST "$API_BASE_URL/api/v1/memory" -H "Content-Type: application/json" -H "x-user-id: demo-user" -d '{"memory_scope":"project","memory_type":"project","project_id":"{project_id}","visibility":"project","importance_score":0.9,"content":{"core_switch":"10.1.1.1","window":"Sat 02:00"},"auto_embedding":true}'
```

### 6) Hybrid semantic search

```powershell
curl -X POST "$API_BASE_URL/api/v1/memory/semantic-search" -H "Content-Type: application/json" -H "x-user-id: demo-user" -d '{"query_embedding":[0.01,0.02,0.03],"top_k":5,"project_id":"{project_id}","memory_scope":"project","memory_type":"project","min_importance":0.2,"similarity_weight":0.7}'
```

注：query_embedding 维度必须与配置一致。
Note: query_embedding dimensions must match configuration.

### 7) Retry failed embeddings

```powershell
curl -X POST "$API_BASE_URL/api/v1/memory/retry-embeddings?limit=20" -H "x-user-id: demo-user"
```

## C. 前端手工测试 / Frontend Manual Test

1. 确认 `.env` 中 `VITE_API_BASE_URL` 指向后端地址
2. 访问 `http://localhost:5173`
2. Projects 页面创建项目
3. Resources 页面创建 Agent/Tool/Skill/MCP
4. Workbench 页面创建 session 并发送消息
5. 观察 backend 日志和 API 返回

## D. 常见失败排查 / Common Troubleshooting

- `403 No access to project`: `x-user-id` 与 project member 不匹配
- `embedding generation failed`: provider 配置错误或模型服务不可达
- `query_embedding dimension must be ...`: 向量维度不匹配
- `vector extension` error: PostgreSQL 未安装/启用 pgvector
