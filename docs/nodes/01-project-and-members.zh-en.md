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
- `POST /api/v1/projects/{project_id}/members`

## 关键字段 / Key Fields

- `name`: 项目名 / project name
- `description`: 项目描述 / project description
- `owner_id`: 项目创建者（由 `x-user-id` 决定） / owner inferred from `x-user-id`
- `members`: 被授权成员列表 / authorized members

## 权限模型 / Access Model

中文：
- owner 可以加成员
- owner + members 可访问项目内资源

English:
- owner can add members
- owner + members can access project-scoped resources

## 代码位置 / Code References

- `backend/app/api/v1/projects.py`
- `backend/app/services/postgres_store.py`
- `backend/app/db/models.py` (`projects`, `project_members`)
