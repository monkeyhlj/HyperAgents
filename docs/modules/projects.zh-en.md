# Projects Module Guide / Projects 模块说明

状态 / Status: Implemented and code-aligned.

## Purpose / 作用

中文：
用于管理项目实体、成员关系和项目级权限边界。项目是 HyperAgents 的主要隔离边界，资源、会话、Provider Connection 和成员权限都挂在项目下。

English:
Manages project entities, member relationships, and project-level permission boundaries. A project is the main isolation boundary for resources, sessions, Provider Connections, and permissions.

## Current Scope / 当前范围

1. 项目创建、查看、编辑、删除。 / Create, view, edit, and delete projects.
2. 项目成员添加与移除。 / Add and remove project members.
3. member manager 授权与撤销。 / Grant and revoke member-manager permissions.
4. 项目级资源、会话和 Provider Connection 隔离。 / Isolate resources, sessions, and Provider Connections at the project level.

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

- 项目 owner 拥有完整管理权限。 / The project owner has full management permissions.
- 项目成员可访问项目内 project 可见资源。 / Project members can access resources with project visibility inside the project.
- member manager 可添加成员，但不能移除成员或撤销授权。 / A member manager can add members, but cannot remove members or revoke delegation.
- private 资源仍受 owner 约束，不因项目成员身份自动公开。 / Private resources remain owner-scoped and are not exposed automatically to project members.

## Test Checklist / 测试清单

1. 创建项目并确认 owner 自动成为成员。 / Create a project and confirm the owner is added as a member automatically.
2. 编辑项目名称和描述。 / Edit the project name and description.
3. 添加普通成员并验证其能看到项目。 / Add a regular member and confirm they can see the project.
4. 授权 member manager 后，验证其可以添加成员。 / Grant member-manager permission and confirm the delegate can add members.
5. 验证普通成员不能删除项目、移除成员或撤销授权。 / Confirm regular members cannot delete the project, remove members, or revoke delegation.
6. 删除项目后，相关项目级列表不再返回该项目。 / After deleting a project, related project-level lists should no longer return it.
