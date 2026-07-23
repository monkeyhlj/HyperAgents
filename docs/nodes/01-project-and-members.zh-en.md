# Node 01: Project and Members (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## 节点职责 / Responsibilities

中文：
Project 是系统一级边界。Agent、Workflow、Tool、Skill、MCP、Knowledge Base、Chat Session、Memory 与 Provider Connection 都围绕 Project 进行隔离和授权。

English:
Project is the first-class boundary. Agents, Workflows, Tools, Skills, MCPs, Knowledge Bases, Chat Sessions, Memory, and Provider Connections are isolated and authorized around projects.

## 对应接口 / API Endpoints

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/members`
- `DELETE /api/v1/projects/{project_id}/members/{member_id}`
- `POST /api/v1/projects/{project_id}/member-managers`
- `DELETE /api/v1/projects/{project_id}/member-managers/{member_id}`

## 关键字段 / Key Fields

- `name`: 项目名 / project name
- `description`: 项目描述 / project description
- `owner_id`: 项目创建者，优先来自 Bearer token；本地兼容时可来自 `x-user-id` / owner inferred from Bearer token first; `x-user-id` is a local compatibility fallback
- `members`: 被授权成员列表 / authorized members
- `member_managers`: 被 owner 委托、可执行“添加成员”的用户列表 / delegated users who can add members

## 权限模型 / Access Model

- owner 可以查看、编辑、删除项目。
- owner 可以添加/删除成员。
- owner 可以授予/撤销某成员的“添加成员”权限。
- member manager 只能添加成员，不能删除成员或撤销授权。
- owner + members 可访问项目内 project 可见资源。
- private 资源仍只对资源 owner 可见。

## 代码位置 / Code References

- `backend/app/api/v1/projects.py`
- `backend/app/api/deps.py`
- `backend/app/services/postgres_store.py`
- `backend/app/db/models.py`
- `backend/alembic/versions/0005_project_member_permissions.py`
