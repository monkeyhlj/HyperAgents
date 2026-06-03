# HyperAgents (中文)

语言切换: [English](README.en.md) | [入口](README.md)

HyperAgents 是一个面向团队的 Agent Operating System 风格平台，用于构建、运行和测试 AI Agent。

## V1 范围

- Project-first 模型（所有资源都归属于项目）
- 资源管理包括：
  - Agent
  - Workflow
  - Tool
  - Skill
  - MCP Server
  - Knowledge Base
- 资源可见性策略：
  - `private`（仅创建者）
  - `project`（项目成员）
  - `public`（所有人）
- 提供项目级对话工作台用于测试资源组合
- 支持双模式：
  - 可视化管理（Web UI）
  - 代码优先扩展（后端 Runtime 抽象）

## Monorepo 结构

- `backend`：FastAPI 服务（API + Runtime 骨架）
- `frontend`：Vue 3 + Vite 应用

## 快速开始

### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

启动后端前请先创建工作区环境文件：

```bash
copy .env.example .env
```

然后编辑 `.env`，至少设置：

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hyperagents
```

可选：本地自动建表（开发模式）：

```bash
AUTO_CREATE_TABLES=true
```

默认建议通过 Alembic 管理建表与迁移。

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端地址：`http://localhost:5173`，后端地址：`http://localhost:8000`。

## 下一阶段里程碑

- 持久化增强到 PostgreSQL + pgvector
- 增加 Redis 作业队列与 Runtime Worker
- 接入真实模型 Provider（OpenAI、本地 vLLM/Ollama）
- 完善 MCP 传输与鉴权
- 增加执行沙箱（Docker / Firecracker）
- 引入 RBAC 与组织级协作

## Memory Service V1

Memory 已作为平台级服务，具备显式 scope 与 visibility。

支持的 scope/type：

- `conversation`
- `project`
- `agent`
- `execution`
- `global`

可见性：

- `private`
- `project`
- `public`

API：

- `POST /api/v1/memory` 写入记忆
- `GET /api/v1/memory` 按过滤条件查询
- `POST /api/v1/memory/semantic-search` 混合检索（向量相似度 + importance）
- `POST /api/v1/memory/retry-embeddings` 处理 embedding 重试队列

核心字段：

- `project_id`, `agent_id`, `session_id`, `workflow_run_id`
- `importance_score`（0~1）
- `content`（JSON）
- `embedding_status`（`skipped` / `pending` / `succeeded` / `failed`）
- `embedding`, `embedding_provider`, `embedding_model`, `embedding_error`

### 语义检索请求示例

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

`query_embedding` 与存储向量的维度必须与 `MEMORY_EMBEDDING_DIMENSIONS` 一致（默认 1536）。

混合评分公式：

- `hybrid_score = similarity_weight * similarity_score + (1 - similarity_weight) * importance_score`

## Alembic 迁移

迁移目录在 `backend/alembic`。

执行迁移：

```bash
cd backend
alembic upgrade head
```

结构变更后创建迁移：

```bash
cd backend
alembic revision --autogenerate -m "describe change"
```

## LLM Provider 适配层

Runtime 通过 Agent 资源配置进行统一 Provider 路由。

当前支持：

- `openai`
- `localhost`（别名：`ollama`, `vllm`）

环境变量统一从工作区 `.env` 读取（模板见 `.env.example`）。

LLM 相关主要配置：

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

当发送聊天请求并传入 `agent_id` 时，Runtime 会读取该 Agent 资源中的 `model_provider`、`model_name` 和 `config.system_prompt`。

## 自动 Memory 向量化

Memory 写入支持服务端自动生成 embedding，客户端无需手工传向量。

`POST /api/v1/memory` 支持字段：

- `auto_embedding`（默认 `true`）
- `retry_on_embedding_failure`（默认 `true`）
- `embedding_provider`（可选覆盖，`openai` / `localhost`）
- `embedding_model`（可选覆盖）
- `embedding_input`（可选自定义文本，不传则使用 content 的规范化 JSON）

当 `auto_embedding=true` 时，后端会自动生成并存储向量。

若 embedding 生成失败：

- memory 写入仍成功
- `embedding_status` 置为 `failed`
- 自动入重试队列
- 响应返回后触发一次异步重试

也可手工批量触发重试：

- `POST /api/v1/memory/retry-embeddings?limit=20`

## Registry API（MCP / Tool / Skill）

项目级创建：

- `POST /api/v1/registry/projects/{project_id}/mcp`
- `POST /api/v1/registry/projects/{project_id}/tool`
- `POST /api/v1/registry/projects/{project_id}/skill`

项目内查询（支持 visibility 过滤）：

- `GET /api/v1/registry/projects/{project_id}/mcp?visibility=project`
- `GET /api/v1/registry/projects/{project_id}/tool?visibility=private`
- `GET /api/v1/registry/projects/{project_id}/skill?visibility=public`

跨项目公开列表：

- `GET /api/v1/registry/public/mcp`
- `GET /api/v1/registry/public/tool`
- `GET /api/v1/registry/public/skill`
