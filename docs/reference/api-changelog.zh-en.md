# API Changelog (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [测试手册](../guides/testing-playbook.zh-en.md)

## Versioning Policy

中文：
当前项目处于快速迭代阶段，统一使用 v1 路由前缀，采用“文档先行 + 小版本增量兼容”的方式推进。

English:
The project is in active iteration. We keep `/api/v1/*` as the stable prefix and evolve with additive, backward-compatible updates whenever possible.

## 2026-06-03 (Current)

### Added: Auth APIs

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

说明:
- 登录成功返回 `access_token` (Bearer)
- `x-user-id` 仍可作为兼容回退方式（建议迁移到 Bearer）

### Added: Project Detail API

- `GET /api/v1/projects/{project_id}`

说明:
- 返回项目基础信息 + members
- 需通过项目成员权限检查

### Added: Project Member Management

- `POST /api/v1/projects/{project_id}/members`
- `DELETE /api/v1/projects/{project_id}/members/{member_id}`

### Added: Chat Session History APIs

- `GET /api/v1/chat/projects/{project_id}/sessions`
- `GET /api/v1/chat/sessions/{session_id}/messages`

### Added: Runtime Run Timeline APIs

- `GET /api/v1/chat/sessions/{session_id}/runs`
- `GET /api/v1/chat/runs/{run_id}/events`

### Changed: Chat Send Message Response

- Endpoint: `POST /api/v1/chat/sessions/{session_id}/messages`
- New response field: `run_id`

示例响应:

```json
{
  "session_id": "a-session-id",
  "role": "assistant",
  "text": "...",
  "run_id": "a-run-id"
}
```

### Added: Worker Queue Mode for Memory Retry

- Endpoint: `POST /api/v1/memory/retry-embeddings`
- New query parameter: `enqueue=true|false`
- Response新增字段：
  - `queued`
  - `task_id`
  - `message`

示例:

```http
POST /api/v1/memory/retry-embeddings?limit=20&enqueue=true
Authorization: Bearer <token>
```

## Backward Compatibility Notes

1. `x-user-id` header fallback is still accepted by dependency resolver.
2. Existing project/resource/chat core APIs remain available.
3. New fields are additive; previous clients can ignore unknown fields safely.

## Migration Checklist for Consumers

1. 从 `x-user-id` 迁移到 Bearer token。
2. 对 chat message 响应兼容 `run_id` 字段。
3. 若接入任务队列，处理 memory retry 的 `queued/task_id` 返回值。
4. 若前端需要可观测性，接入 runs/events API。

## Next Planned Changes

1. Runtime run 增加 token usage 与 latency 分段。
2. Runtime events 增加 tool/mcp/memory 级别事件。
3. Worker 增加任务状态查询 API（task list/detail/retry）。
