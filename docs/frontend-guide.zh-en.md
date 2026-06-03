# Frontend Guide (中文 + English)

导航 / Navigation: [返回项目首页](../README.md) | [文档首页](README.md) | [测试手册](testing-playbook.zh-en.md)

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
- 创建会话，加载项目下历史会话。
- 打开历史会话并查看消息。
- 发送消息到 runtime。

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
5. 在 Workbench 选择项目，创建会话并发送消息。

## 7) Troubleshooting

- 登录失败（401）：检查账号密码，确认后端 auth 路由已加载。
- 项目无权限（403）：当前用户不在项目成员内。
- Workbench 无会话：先在当前选中项目下创建 session。
- 前端空白页：检查 VITE_API_BASE_URL 与后端端口是否一致。
