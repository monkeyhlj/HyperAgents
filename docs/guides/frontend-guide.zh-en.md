# Frontend Guide (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [测试手册](testing-playbook.zh-en.md)

## 1) 前端目标 / Frontend Scope

中文：
前端工作台基于 Vue 3 + View UI Plus，提供登录、项目管理、项目详情、资源查看与 Workbench 会话调试。

English:
The frontend workbench is built with Vue 3 + View UI Plus and provides login, project management, project details, resource browsing, and Workbench chat debugging.

## 2) 页面结构 / Pages

1. Login
- 注册 / 登录，获取 Bearer token 并保存会话。

2. Dashboard
- 展示当前登录用户、平台结构摘要与系统状态。

3. Projects
- 创建项目。
- 按项目 ID 或项目名过滤。
- 点击项目名进入详情页。
- 管理成员（添加 / 删除）。

4. Project Detail
- 查看项目基础信息。
- 列出该项目资源。
- 按资源 ID 或资源名过滤。

5. Resources
- 直接按项目 ID 维护资源（agent/workflow/tool/skill/mcp/knowledge_base）。

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
4. 若后续接入 tool/mcp/memory 事件，前端时间线会自动扩展显示。

## 3) API Mapping

- Auth
  - POST /api/v1/auth/register
  - POST /api/v1/auth/login
  - GET /api/v1/auth/me
- Projects
  - GET /api/v1/projects
  - POST /api/v1/projects
  - GET /api/v1/projects/{project_id}
  - POST /api/v1/projects/{project_id}/members
  - DELETE /api/v1/projects/{project_id}/members/{member_id}
- Resources
  - GET /api/v1/resources/projects/{project_id}
  - POST /api/v1/resources/projects/{project_id}
- Chat
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
5. 在 Workbench 选择项目并加载 Agent。
6. 创建会话并发送消息。
7. 在 Run Timeline 中查看 run 与 events。

## 7) Acceptance Checklist

1. 登录后可正常进入 Dashboard，刷新页面不丢失会话。
2. Projects 支持按名称/ID过滤并可进入详情。
3. Project Detail 可查看资源并按名称/ID过滤。
4. Workbench 可选择项目、选择 Agent、创建会话、发送消息。
5. Workbench 可看到 run 列表与事件 timeline。
6. 所有 API 请求都带 Bearer token。

## 8) Troubleshooting

- 登录失败（401）：检查账号密码，确认后端 auth 路由已加载。
- 项目无权限（403）：当前用户不在项目成员内。
- Workbench 无会话：先在当前选中项目下创建 session。
- Workbench 无 Agent：确认项目下已创建 kind=agent 资源。
- Timeline 无数据：确认消息是通过 Workbench 发送且后端已执行最新迁移。
- 前端空白页：检查 VITE_API_BASE_URL 与后端端口是否一致。
