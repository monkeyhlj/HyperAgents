# HyperAgents

HyperAgents 是一个 Project-first 的 Agent Operating System 原型，用于团队构建、编排和测试 AI Agent。系统以项目为边界，统一管理 Agent、Workflow、Tool、Skill、MCP、Knowledge Base 等资源，并通过 FastAPI 后端与 Vue 3 前端提供运行、记忆、注册表和调试工作台能力。

## 核心能力

- 项目优先模型：资源归属项目，并通过 private/project/public 可见性控制访问范围。
- 统一资源系统：支持 agent、workflow、tool、skill、mcp、knowledge_base。
- Runtime 执行层：支持 OpenAI-compatible provider、本地 provider、项目级 Provider Connection，以及 code-mode Agent。
- Memory 服务：支持写入、关键字检索、语义检索、embedding 状态与重试。
- Registry API：支持项目内注册 tool/skill/mcp 与 public registry 浏览。
- 全栈工作台：FastAPI 后端、Vue 3 + Vite 前端、Workbench 会话调试与 Run Timeline。

## 仓库结构

- `backend`: FastAPI API、SQLAlchemy 模型、Alembic 迁移、runtime、memory、worker。
- `frontend`: Vue 3 前端，覆盖登录、项目、资源、Provider Connection、Workbench。
- `docs`: 中英双语文档站，包含快速开始、模块说明、架构节点、测试与运维手册。
- `scripts`: Windows PowerShell 与 Linux/macOS Bash 启动脚本。
- `.env.example`: 根目录统一环境变量模板。

## 快速开始

```powershell
copy .env.example .env
./scripts/start-backend.ps1 -Environment dev -RunMigrations
./scripts/start-frontend.ps1 -Environment dev -Install
```

后端默认地址：`http://localhost:8000`

前端默认地址：`http://localhost:5173`

基础健康检查：

```powershell
curl http://localhost:8000/health
```

预期返回：

```json
{"status":"ok"}
```

## 文档入口

- [文档门户](docs/README.md)
- [快速开始](docs/guides/quick-start.zh-en.md)
- [代码与 API 对齐参考](docs/reference/code-api-map.zh-en.md)
- [测试手册](docs/guides/testing-playbook.zh-en.md)
- [运行与 Worker](docs/guides/runtime-run-worker.zh-en.md)

## 当前状态

项目仍在快速迭代中。请以代码、Alembic 迁移和 `docs/reference/code-api-map.zh-en.md` 作为判断当前能力边界的主要依据。
