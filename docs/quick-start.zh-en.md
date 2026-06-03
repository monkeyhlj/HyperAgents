# Quick Start (中文 + English)

导航 / Navigation: [返回项目首页](../README.md) | [文档首页](README.md) | [中文 README](../README.zh.md) | [English README](../README.en.md)

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

## 4) 前端命令 / Frontend Commands

```powershell
cd frontend
npm install
npm run dev
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
