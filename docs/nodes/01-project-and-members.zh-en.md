# Node 01: Project and Members (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## 节点职责 / Responsibilities

中文：
Project 是系统一级资源，所有 Agent、Workflow、Tool、Skill、MCP、KB、Memory 都应归属于某个 Project。

English:
Project is the first-class resource. All Agent/Workflow/Tool/Skill/MCP/KB/Memory objects should belong to a Project.

## 对应接口 / API Endpoints

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `PATCH /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/members`
- `DELETE /api/v1/projects/{project_id}/members/{member_id}`
- `POST /api/v1/projects/{project_id}/member-managers`
- `DELETE /api/v1/projects/{project_id}/member-managers/{member_id}`

## 关键字段 / Key Fields

- `name`: 项目名 / project name
- `description`: 项目描述 / project description
- `owner_id`: 项目创建者（由 `x-user-id` 决定） / owner inferred from `x-user-id`
- `members`: 被授权成员列表 / authorized members
- `member_managers`: 被 owner 委托、可执行“添加成员”的用户列表 / delegated users who can add members

## 权限模型 / Access Model

中文：
- owner 可以添加/删除成员
- owner 可以授予/撤销某成员的“添加成员”权限（member manager）
- member manager 只能添加成员，不能删除成员
- owner + members 可访问项目内资源

English:
- owner can add/remove members
- owner can grant/revoke delegated "add member" permission (member manager)
- member manager can add members but cannot remove members
- owner + members can access project-scoped resources

## 代码位置 / Code References

- `backend/app/api/v1/projects.py`
- `backend/app/services/postgres_store.py`
- `backend/app/db/models.py` (`projects`, `project_members`, `project_member_permissions`)
- `backend/alembic/versions/0005_project_member_permissions.py`
