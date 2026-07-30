# HyperAgents (中文)

语言 / Language: [首页](README.md) | [English](README.en.md) | [文档入口](docs/README.md) | [在线文档](https://monkeyhlj.github.io/HyperAgents/)

HyperAgents 是一个 Project-first 的 Agent Operating System 原型，用于团队构建、管理、绑定、编排和测试 AI Agent。它不是单一聊天 Demo，而是围绕 Project、Resource、Workbench、Skill、Knowledge、Workflow 和 My Files 组织完整的 Agent 工作空间。

## 核心能力

- 项目优先模型：资源归属项目，并通过 `private` / `project` / `public` 控制可见性。
- 统一资源系统：支持 Agents、Tools、Skills、MCPs、Knowledge Bases、Workflows。
- Workbench：支持持久化会话、Agent 选择、运行状态、Skill/Knowledge 使用标记、文件输出。
- Skills：支持上传 Skill 包、渐进式披露、绑定 Agent、脚本感知执行路径。
- Knowledge：支持文档上传、检索参数、Agent 绑定和问答增强。
- Workflows：支持图形化节点编辑、分支路由、JSON 同步、Test 运行、Run History。
- My Files：支持上传输入文件、保存生成文件、搜索、分页、下载和删除清理。
- Provider：支持 OpenAI-compatible profile 和项目级 Provider Connection。
- Runtime：支持 run/events 运行轨迹、HTTP 日志配置和可选 Worker 队列模式。

## 仓库结构

- `backend`: FastAPI API、runtime、skill/workflow 执行、SQLAlchemy 模型、Alembic 迁移。
- `frontend`: Vue 3 + Vite 前端，覆盖 Dashboard、Projects、Resources、Workbench、Workflows、My Files。
- `docs`: 中英双语文档站源码，包含模块说明、快速开始、设计计划、运维参考。
- `scripts`: Windows PowerShell 与 Linux/macOS Bash 启动脚本。
- `.env.example`: 根目录统一环境变量模板。

## 快速开始

1. 复制环境变量模板：

```powershell
copy .env.example .env
```

2. 启动后端和前端：

```powershell
./scripts/start-backend.ps1 -Environment dev -RunMigrations
./scripts/start-frontend.ps1 -Environment dev -Install
```

3. 打开服务：

- 后端：`http://localhost:8000`
- 前端：`http://localhost:5173`
- API 文档：`http://localhost:8000/docs`

4. 健康检查：

```powershell
curl http://localhost:8000/health
```

预期返回：

```json
{"status":"ok"}
```

## Provider 配置

Provider Profile 会映射到同名前缀的环境变量。例如 `provider_profile=nvidia` 会读取：

```bash
NVIDIA_API_KEY=<your_key>
NVIDIA_BASE_URL=<compatible_endpoint>
NVIDIA_DEFAULT_MODEL=<model_name>
```

也可以通过项目级 Provider Connection 在数据库中保存加密后的 endpoint credential。

## Worker 模式

普通本地测试不需要单独启动 Worker。Chat、Resource、Workbench、Workflow 测试都可以由 API 进程完成。

需要队列异步任务时再开启：

```bash
WORKER_ENABLED=true
WORKER_BROKER_URL=redis://localhost:6379/0
WORKER_BACKEND_URL=redis://localhost:6379/1
```

启动 Celery Worker：

```powershell
cd backend
.venv\Scripts\activate
celery -A app.workers.celery_app.celery_app worker -l info
```

## 推荐体验路径

1. 创建 Project。
2. 创建或导入 Agent、Tool、Skill、MCP、Knowledge Base。
3. 给 Agent 绑定 Skill 和 Knowledge Base。
4. 在 Workbench 里测试 Agent，并查看运行状态与输出文件。
5. 在 My Files 中上传输入文件、下载生成文件。
6. 创建 Workflow，用图形化画布连接多个 Agent 节点并运行测试。

## 文档入口

- [文档门户](docs/README.md)
- [快速开始](docs/guides/quick-start.zh-en.md)
- [前端使用说明](docs/guides/frontend-guide.zh-en.md)
- [Resources 模块](docs/modules/resources.zh-en.md)
- [Workbench 模块](docs/modules/workbench.zh-en.md)
- [Workflows 模块](docs/modules/workflows.zh-en.md)
- [代码与 API 对齐参考](docs/reference/code-api-map.zh-en.md)

## 当前状态

项目仍在快速迭代中。当前重点是提升通用 Skill 执行质量、优化 Workflow 编排体验，并让文档对首次阅读的用户更清晰。请以代码、Alembic 迁移和 `docs/reference/code-api-map.zh-en.md` 作为判断当前能力边界的主要依据。
