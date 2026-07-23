# Projects Module Guide / Projects 模块说明

状态 / Status: Implemented and code-aligned.

## Purpose / 作用

中文：
用于管理项目实体、成员关系和项目级权限边界。项目是 HyperAgents 的主要隔离边界，资源、会话、Provider Connection 和成员权限都挂在项目下。

English:
Manages project entities, member relationships, and project-level permission boundaries. A project is the main isolation boundary for resources, sessions, Provider Connections, and permissions.

## Current Scope / 当前范围

1. 项目创建、查看、编辑、删除。
2. 项目成员添加与移除。
3. member manager 授权与撤销。
4. 项目级资源、会话和 Provider Connection 隔离。

## API Mapping / API 对照

- `GET /api/v1/projects`: 查询当前用户可访问项目。
- `POST /api/v1/projects`: 创建项目。
- `GET /api/v1/projects/{project_id}`: 查看项目详情。
- `PATCH /api/v1/projects/{project_id}`: 更新项目名称或描述。
- `DELETE /api/v1/projects/{project_id}`: 删除项目。
- `POST /api/v1/projects/{project_id}/members`: 添加成员。
- `DELETE /api/v1/projects/{project_id}/members/{member_id}`: 移除成员。
- `POST /api/v1/projects/{project_id}/member-managers`: 授权成员添加成员。
- `DELETE /api/v1/projects/{project_id}/member-managers/{member_id}`: 撤销授权。

## Permission Notes / 权限说明

- 项目 owner 拥有完整管理权限。
- 项目成员可访问项目内 project 可见资源。
- member manager 可添加成员，但不能移除成员或撤销授权。
- private 资源仍受 owner 约束，不因项目成员身份自动公开。

## Test Checklist / 测试清单

1. 创建项目并确认 owner 自动成为成员。
2. 编辑项目名称和描述。
3. 添加普通成员并验证其能看到项目。
4. 授权 member manager 后，验证其可以添加成员。
5. 验证普通成员不能删除项目、移除成员或撤销授权。
6. 删除项目后，相关项目级列表不再返回该项目。
