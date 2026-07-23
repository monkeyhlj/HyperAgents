# Frontend Guide (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [测试手册](testing-playbook.zh-en.md)

## 1) 前端目标 / Frontend Scope

中文：
前端工作台基于 Vue 3 + View UI Plus，提供登录、项目管理、项目详情、资源管理、Provider Connection 和 Workbench 会话调试。

English:
The frontend workbench is built with Vue 3 + View UI Plus and provides login, project management, project details, resource management, Provider Connections, and Workbench chat debugging.

## 2) 页面结构 / Pages

1. Login
- 注册 / 登录，获取 Bearer token 并保存会话。

2. Dashboard
- 展示当前登录用户、平台结构摘要与系统状态。

3. Projects
- 创建、编辑、删除项目。
- 按项目 ID 或项目名过滤。
- 点击项目名进入详情页。
- 管理成员（添加 / 删除）和 member manager 授权。

4. Project Detail
- 查看项目基础信息。
- 列出该项目资源。
- 按资源 ID 或资源名过滤。

5. Resources
- 按类型维护资源（agent/workflow/tool/skill/mcp/knowledge_base）。
- 支持默认资源模板、我的资源列表、创建、编辑、删除。
- Agent 创建/编辑支持 Env profile 与 URL + API Key 两种 provider 配置方式。
- MCP 创建/编辑支持 Quick Test 和保存后的行级 Test。

6. Workbench
- 先选择项目（支持按项目名/ID过滤）。
- 加载当前项目 Agent，下拉选择 agent_id。
- 创建会话，加载项目下历史会话。
- 打开历史会话并查看消息。
- 查看 Runtime Run Timeline 与事件。
- 发送消息到 runtime。

### Workbench 运行可观测性 / Runtime Observability in Workbench

1. 发送消息后，后端会创建 run 记录并返回 run_id。
2. Workbench 的 Run Timeline 列表显示每次运行状态：running/succeeded/failed。
3. 点击某个 run 的 Events 可以查看分阶段事件：
- runtime: 执行开始/完成/失败
- agent: 选中的 agent 与模型信息
- code/tool/mcp: code-mode Agent 执行、Tool 调用与 MCP 调用信息
4. 后续接入更多事件时，前端时间线可按事件 stage 扩展显示。

## 3) API Mapping

- Auth
  - POST /api/v1/auth/register
  - POST /api/v1/auth/login
  - GET /api/v1/auth/me
  - GET /api/v1/auth/users/search
- Projects
  - GET /api/v1/projects
  - POST /api/v1/projects
  - GET /api/v1/projects/{project_id}
  - PATCH /api/v1/projects/{project_id}
  - DELETE /api/v1/projects/{project_id}
  - POST /api/v1/projects/{project_id}/members
  - DELETE /api/v1/projects/{project_id}/members/{member_id}
  - POST /api/v1/projects/{project_id}/member-managers
  - DELETE /api/v1/projects/{project_id}/member-managers/{member_id}
- Resources
  - GET /api/v1/resources/defaults
  - GET /api/v1/resources/mine
  - GET /api/v1/resources/projects/{project_id}
  - POST /api/v1/resources/projects/{project_id}
  - GET /api/v1/resources/{resource_id}
  - PATCH /api/v1/resources/{resource_id}
  - DELETE /api/v1/resources/{resource_id}
  - POST /api/v1/resources/preview-chat
- Provider Connections
  - GET /api/v1/provider-connections/projects/{project_id}
  - POST /api/v1/provider-connections/projects/{project_id}
  - PATCH /api/v1/provider-connections/{connection_id}
  - POST /api/v1/provider-connections/projects/{project_id}/probe-models
  - POST /api/v1/provider-connections/projects/{project_id}/test
  - POST /api/v1/provider-connections/{connection_id}/test
- Registry/MCP
  - POST /api/v1/registry/mcp/probe
- Chat
  - GET /api/v1/chat/code-execution-audits
  - POST /api/v1/chat/projects/{project_id}/sessions
  - GET /api/v1/chat/projects/{project_id}/sessions
  - GET /api/v1/chat/sessions/{session_id}/messages
  - GET /api/v1/chat/sessions/{session_id}/runs
  - GET /api/v1/chat/runs/{run_id}/events
  - POST /api/v1/chat/sessions/{session_id}/messages

## 4) Frontend Run Steps

```powershell
cd frontend
npm install
npm run dev
```

默认前端地址：
Default frontend URL:
- http://localhost:5173

## 5) Required Env

在根目录 .env 中配置：
Configure in workspace root .env:

- VITE_API_BASE_URL=http://localhost:8000

## 6) Typical Flow

1. 登录或注册。
2. 在 Projects 创建项目。
3. 点项目名进入 Project Detail 查看资源。
4. 在 Resources 页面创建 Agent。
5. 如需自定义模型连接，在 Agent 表单中使用 URL + API Key 加载模型并测试。
6. 在 Workbench 选择项目并加载 Agent。
7. 创建会话并发送消息。
8. 在 Run Timeline 中查看 run 与 events。

## 7) Acceptance Checklist

1. 登录后可正常进入 Dashboard，刷新页面不丢失会话。
2. Projects 支持按名称/ID过滤并可进入详情。
3. Project Detail 可查看资源并按名称/ID过滤。
4. Resources 可创建、编辑、删除资源，并可测试 Agent/MCP。
5. Workbench 可选择项目、选择 Agent、创建会话、发送消息。
6. Workbench 可看到 run 列表与事件 timeline。
7. 所有 API 请求都带 Bearer token。

## 8) Troubleshooting

- 登录失败（401）：检查账号密码，确认后端 auth 路由已加载。
- 项目无权限（403）：当前用户不在项目成员内。
- Workbench 无会话：先在当前选中项目下创建 session。
- Workbench 无 Agent：确认项目下已创建 kind=agent 资源。
- Timeline 无数据：确认消息是通过 Workbench 发送且后端已执行最新迁移。
- Provider Connection 测试失败：检查 Base URL、API Key、模型名和网络连通性。
- MCP 测试失败：检查 endpoint_url、headers、timeout_seconds 和 MCP server 的 `/health`、`/tools`。
- 前端空白页：检查 VITE_API_BASE_URL 与后端端口是否一致。
