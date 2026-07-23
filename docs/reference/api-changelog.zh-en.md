# API Changelog (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [代码与 API 对齐](code-api-map.zh-en.md) | [测试手册](../guides/testing-playbook.zh-en.md)

## Versioning Policy

中文：
当前项目处于快速迭代阶段，统一使用 `/api/v1/*` 路由前缀，优先采用增量兼容方式演进。当前完整 API 面以 [code-api-map.zh-en.md](code-api-map.zh-en.md) 为准。

English:
The project is in active iteration. We keep `/api/v1/*` as the stable prefix and prefer additive, backward-compatible changes. The current full API surface is tracked in [code-api-map.zh-en.md](code-api-map.zh-en.md).

## 2026-07-24 (Current)

### Added: Provider Connection APIs

- `POST /api/v1/provider-connections/projects/{project_id}/probe-models`
- `POST /api/v1/provider-connections/projects/{project_id}/test`
- `GET /api/v1/provider-connections/projects/{project_id}`
- `POST /api/v1/provider-connections/projects/{project_id}`
- `GET /api/v1/provider-connections/{connection_id}`
- `PATCH /api/v1/provider-connections/{connection_id}`
- `POST /api/v1/provider-connections/{connection_id}/test`
- `DELETE /api/v1/provider-connections/{connection_id}`

说明：
- API Key 加密保存到 `provider_connections` 表。
- Agent 可通过 `provider_connection_id` 绑定项目级模型连接。
- 生产环境应设置 `PROVIDER_CONNECTION_SECRET_KEY`。

### Changed: Resource APIs

- `GET /api/v1/resources/defaults` returns default resource templates.
- `GET /api/v1/resources/mine` returns owned/visible resources with project names.
- `POST /api/v1/resources/preview-chat` validates draft Agent config before saving.
- Resource payloads include `provider_connection_id`.

### Changed: Chat Runtime

- `ChatMessageRequest` supports `engine_type`, `provider_profile`, `temperature`, `max_iterations`, and `mcp_ids` overrides.
- `ChatMessageResponse` includes `used_tools` and `used_mcps`.
- `GET /api/v1/chat/code-execution-audits` exposes recent code-mode execution audit rows.
- Optional `engine_type=react` path is available for ReAct-style reasoning/action execution.

### Added: MCP Probe and MCP Usage

- `POST /api/v1/registry/mcp/probe` validates `streamable_http` MCP endpoints.
- code-mode Agents can call MCP tools through `call_mcp(...)`.
- Workbench displays MCP usage tags from `used_mcps`.

### Added: Project Member Manager APIs

- `POST /api/v1/projects/{project_id}/member-managers`
- `DELETE /api/v1/projects/{project_id}/member-managers/{member_id}`

## 2026-06-03

### Added: Auth APIs

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

说明:
- 登录成功返回 `access_token` (Bearer)。
- `x-user-id` 仍可作为本地开发兼容回退方式，正式客户端建议使用 Bearer token。

### Added: Project Detail API

- `GET /api/v1/projects/{project_id}`

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
- Added response field: `run_id`

### Added: Worker Queue Mode for Memory Retry

- Endpoint: `POST /api/v1/memory/retry-embeddings`
- Query parameter: `enqueue=true|false`
- Response fields: `queued`, `task_id`, `message`

## Backward Compatibility Notes

1. `x-user-id` header fallback is still accepted by dependency resolver for local compatibility.
2. Existing project/resource/chat core APIs remain available.
3. New fields are additive; previous clients can ignore unknown fields safely.

## Migration Checklist for Consumers

1. Prefer Bearer token over `x-user-id`.
2. Handle `run_id`, `used_tools`, and `used_mcps` in chat message responses.
3. If using Provider Connections, run Alembic through `0006_provider_connections` or `head`.
4. If using queue mode, handle memory retry `queued/task_id` response fields.
5. Keep frontend API mappings synchronized with [code-api-map.zh-en.md](code-api-map.zh-en.md).

## Next Planned Changes

1. Runtime run token usage and latency breakdown.
2. Task status APIs for Worker jobs.
3. Dedicated workflow runtime APIs.
4. Stronger registry governance for public reusable resources.
