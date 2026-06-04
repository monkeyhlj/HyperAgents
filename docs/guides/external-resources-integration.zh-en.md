# External Resources Integration Guide (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## 你应该优先接入什么 / What to Add First

中文建议优先级：
1. 模型资源：OpenAI + localhost
2. Tool：常用业务 API（告警、工单、CMDB）
3. MCP：跨系统协议能力（GitHub/Jira/DB 等）
4. Skill：把多个 Tool 封装成场景能力
5. Knowledge Base：文档知识（手册、SOP、FAQ）

Recommended priority:
1. Model resources: OpenAI + localhost
2. Tools: domain APIs (alerting, ticketing, CMDB)
3. MCP: protocol-based integrations (GitHub/Jira/DB)
4. Skills: compose multiple tools into scenario capability
5. Knowledge base: manuals, SOPs, FAQ

## 一、如何添加 Agent 模型资源 / Add Agent Model Resource

### API

`POST /api/v1/resources/projects/{project_id}`

示例（OpenAI）:

```json
{
  "kind": "agent",
  "name": "net-agent-openai",
  "description": "network assistant",
  "visibility": "project",
  "model_provider": "openai",
  "model_name": "gpt-4o-mini",
  "config": {
    "system_prompt": "You are a network troubleshooting assistant."
  }
}
```

示例（localhost）:

```json
{
  "kind": "agent",
  "name": "net-agent-local",
  "description": "local llm agent",
  "visibility": "project",
  "model_provider": "localhost",
  "model_name": "qwen2.5:7b",
  "config": {
    "system_prompt": "Answer with concise operational steps."
  }
}
```

### 默认模板文件 / Default Resource Templates

系统默认资源模板保存在：`backend/app/core/default_resources.json`

- 这里只放模板，不放真实密钥。
- 前端会把默认模板展示为可选项，用户选择后再创建为项目资源。
- 模板中的 `provider_profile` 用于映射环境变量前缀，例如 `zhipu` -> `ZHIPU_API_KEY`、`ZHIPU_BASE_URL`、`ZHIPU_DEFAULT_MODEL`。

If you need a new provider, add a new template entry here and provide the matching env-prefix credentials in `.env`.

## 二、如何添加 Tool / Skill / MCP / KB

统一接口：
`POST /api/v1/resources/projects/{project_id}`

- Tool: `kind=tool`
- Skill: `kind=skill`
- MCP: `kind=mcp`
- KB: `kind=knowledge_base`

建议把接入配置放在 `config` 字段，例如：
- endpoint
- auth type
- scopes
- timeout
- schema

## 三、如何添加 Registry 项 / Add Registry Items

### 项目内注册 / Project-scoped

- `POST /api/v1/registry/projects/{project_id}/tool`
- `POST /api/v1/registry/projects/{project_id}/skill`
- `POST /api/v1/registry/projects/{project_id}/mcp`

请求体使用：
- `name`
- `description`
- `visibility`
- `config`

### 公共浏览 / Public registry listing

- `GET /api/v1/registry/public/tool`
- `GET /api/v1/registry/public/skill`
- `GET /api/v1/registry/public/mcp`

## 四、如何添加 Memory 外部依赖 / Memory External Dependencies

1. Embedding provider
- OpenAI Embeddings
- Local embedding endpoint

2. 向量数据库能力
- PostgreSQL + pgvector extension

3. 重试执行器（后续建议）
- 当前是 DB queue + API/BackgroundTasks
- 未来可升级为 Celery/RQ worker

## 五、前端怎么加 / How to Add via Frontend

当前前端已支持：
- Projects 页创建项目
- Resources 页创建资源
- Workbench 页对话测试

建议你下一步在前端新增两个页面：
1. Registry 页面（区分 project/public）
2. Memory 页面（查看 embedding_status 与重试按钮）

## 六、企业环境建议 / Enterprise Recommendations

- 使用 Secret Manager 管理 API Key
- 为 Tool/MCP 增加审计日志与调用限流
- 为 public registry 增加审核流程
- 对关键 provider 增加 health check 与熔断策略

## 七、生产环境配置建议（.env + Secret Manager） / Production Configuration (.env + Secret Manager)

中文：
建议采用“非敏感配置放 .env，敏感配置放 Secret Manager”的分层方式，既兼容当前代码读取环境变量的模式，也便于安全合规审计。

English:
Use a layered model: non-sensitive settings in `.env`, sensitive values in a Secret Manager. This matches the current environment-variable-based code and improves security/compliance.

### 1) 配置分层建议 / Recommended Configuration Split

放入 `.env`（可进配置仓库模板，不放真实密钥）：
- `APP_NAME`, `APP_VERSION`
- `DATABASE_URL`（可使用低权限应用账号，生产建议不含超级权限）
- `CORS_ALLOW_ORIGINS`
- `OPENAI_BASE_URL`, `OPENAI_DEFAULT_MODEL`, `OPENAI_EMBEDDING_MODEL`
- `LOCALHOST_LLM_BASE_URL`, `LOCALHOST_DEFAULT_MODEL`, `LOCALHOST_EMBEDDING_MODEL`
- `RUNTIME_DEFAULT_PROVIDER`, `EMBEDDING_PROVIDER`
- `MODEL_REQUEST_TIMEOUT_SECONDS`, `MEMORY_EMBEDDING_DIMENSIONS`

Store in Secret Manager (never commit to Git):
- `OPENAI_API_KEY`
- 数据库高敏感凭据（若与应用配置分离）
- 第三方 Tool/MCP 凭据（Token、Client Secret、Webhook Secret）

### 2) 注入方式 / Runtime Injection Pattern

中文：
在容器或部署平台启动阶段，把 Secret Manager 中的密钥注入为同名环境变量（例如 `OPENAI_API_KEY`），应用无需改代码即可读取。

English:
During container/platform startup, inject secrets from Secret Manager as environment variables with the same names (for example, `OPENAI_API_KEY`). No application code changes are required.

常见实现方式 / Common options:
- Kubernetes: External Secrets / CSI Driver -> Pod env
- AWS: Secrets Manager + ECS task/env or EKS external-secrets
- Azure: Key Vault + App Service/Kubernetes bindings
- GCP: Secret Manager + Cloud Run/GKE env injection
- Self-hosted: HashiCorp Vault Agent Template

### 3) 推荐发布流程 / Suggested Release Flow

1. 从 `.env.example` 生成环境模板（dev/staging/prod 各一份）。
2. 在模板中仅保留非敏感默认值，敏感项使用占位符。
3. 在 Secret Manager 创建同名密钥并绑定最小权限访问策略。
4. 在 CI/CD 中进行注入，不在流水线日志打印明文。
5. 部署后通过 `/health` 和一次最小 API 流程做连通性验证。

### 4) 密钥轮换与审计 / Rotation and Audit

中文建议：
- 设定密钥轮换周期（如 30/60/90 天）。
- 轮换时先双轨生效（旧密钥 + 新密钥短暂并存），验证后下线旧密钥。
- 对 Tool/MCP 调用开启审计日志，记录调用方、目标、响应状态与耗时。

English recommendations:
- Define a rotation window (for example 30/60/90 days).
- Use overlap rollout (old + new key briefly) before revoking old keys.
- Enable audit logs for Tool/MCP calls: caller, target, status, and latency.

### 5) 生产检查清单 / Production Checklist

- `.env` 不包含真实密钥，仓库仅保留 `.env.example`
- 敏感变量全部来自 Secret Manager
- 应用账号与数据库账号采用最小权限
- CORS 白名单仅包含正式域名
- Provider 超时与重试参数按 SLA 调优
- 关键外部资源配置了健康检查与告警

## 八、分环境配置示例（dev/staging/prod） / Multi-Environment Examples (dev/staging/prod)

中文：
建议为每个环境维护一份“非敏感配置模板”，例如 `.env.dev`、`.env.staging`、`.env.prod`，并在部署时由平台注入对应密钥。

English:
Maintain one non-sensitive template per environment (for example `.env.dev`, `.env.staging`, `.env.prod`) and inject secrets at deploy time.

### 1) 变量矩阵 / Variable Matrix

| 变量 / Variable | dev | staging | prod | 来源建议 / Source |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | 本地/测试库 | 预发布库 | 生产库（最小权限） | `.env.*` 或 Secret Manager |
| `OPENAI_API_KEY` | 可选（可走本地模型） | 必填 | 必填 | Secret Manager |
| `OPENAI_BASE_URL` | 可空或代理地址 | 代理地址（可选） | 代理/网关地址（推荐） | `.env.*` |
| `LOCALHOST_LLM_BASE_URL` | 本地 `http://localhost:11434/v1` | 内网推理服务地址 | 生产推理网关地址 | `.env.*` |
| `RUNTIME_DEFAULT_PROVIDER` | `localhost` 或 `openai` | 建议 `openai` | 建议 `openai` | `.env.*` |
| `EMBEDDING_PROVIDER` | `openai`/`localhost` | 建议 `openai` | 建议 `openai` | `.env.*` |
| `MODEL_REQUEST_TIMEOUT_SECONDS` | 60~120 | 30~90 | 按 SLA（如 30~60） | `.env.*` |
| `CORS_ALLOW_ORIGINS` | localhost 域名 | 预发前端域名 | 正式前端域名 | `.env.*` |
| `VITE_API_BASE_URL` | 本地 API 地址 | 预发 API 地址 | 正式 API 地址 | `.env.*` |

### 2) 示例模板（非敏感） / Sample Templates (non-sensitive)

`.env.dev`:

```dotenv
APP_NAME=HyperAgents API
DATABASE_URL=postgresql+psycopg://app_dev:***@localhost:5432/hyperagents_dev
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
RUNTIME_DEFAULT_PROVIDER=localhost
EMBEDDING_PROVIDER=localhost
LOCALHOST_LLM_BASE_URL=http://localhost:11434/v1
MODEL_REQUEST_TIMEOUT_SECONDS=90
VITE_API_BASE_URL=http://localhost:8000
```

`.env.staging`:

```dotenv
APP_NAME=HyperAgents API
DATABASE_URL=postgresql+psycopg://app_stage:***@staging-db:5432/hyperagents_stage
CORS_ALLOW_ORIGINS=https://staging.hyperagents.example.com
RUNTIME_DEFAULT_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_REQUEST_TIMEOUT_SECONDS=60
VITE_API_BASE_URL=https://staging-api.hyperagents.example.com
```

`.env.prod`:

```dotenv
APP_NAME=HyperAgents API
DATABASE_URL=postgresql+psycopg://app_prod:***@prod-db:5432/hyperagents
CORS_ALLOW_ORIGINS=https://hyperagents.example.com
RUNTIME_DEFAULT_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_REQUEST_TIMEOUT_SECONDS=45
VITE_API_BASE_URL=https://api.hyperagents.example.com
```

中文说明：上面的 `***` 仅表示占位，不建议在文件中保存真实密码。
English note: `***` is a placeholder only; do not store real passwords in files.

### 3) Secret 命名建议 / Secret Naming Convention

建议命名：
- `hyperagents/dev/OPENAI_API_KEY`
- `hyperagents/staging/OPENAI_API_KEY`
- `hyperagents/prod/OPENAI_API_KEY`
- `hyperagents/<env>/DATABASE_PASSWORD`

这样可以在 CI/CD 中按环境批量注入，避免混用密钥。
This allows environment-scoped secret injection in CI/CD and prevents key mix-ups.

## 九、按环境一键启动脚本（Windows + Linux） / Environment Startup Scripts (Windows + Linux)

项目已提供脚本目录：`scripts/`

- `start-backend.ps1`
- `start-frontend.ps1`
- `start-backend.sh`
- `start-frontend.sh`

脚本行为 / Script behavior:
- 优先加载 `.env.<env>`（如 `.env.dev`）
- 若不存在则回退到 `.env`
- 支持 `dev/staging/prod` 环境参数

### Windows PowerShell

后端（可选执行迁移）：

```powershell
./scripts/start-backend.ps1 -Environment dev -RunMigrations
./scripts/start-backend.ps1 -Environment staging
```

前端（可选安装依赖）：

```powershell
./scripts/start-frontend.ps1 -Environment dev -Install
./scripts/start-frontend.ps1 -Environment prod
```

### Linux/macOS Bash

首次可执行权限：

```bash
chmod +x scripts/start-backend.sh scripts/start-frontend.sh
```

后端：

```bash
./scripts/start-backend.sh --env dev --migrate
./scripts/start-backend.sh --env staging
```

前端：

```bash
./scripts/start-frontend.sh --env dev --install
./scripts/start-frontend.sh --env prod
```
