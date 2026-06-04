# Node 03: Chat and Runtime (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## Chat 节点 / Chat Node

中文：
Chat 是测试入口：先创建 session，再发送 message。可选传 `agent_id` 指定由哪个 Agent 资源执行。

English:
Chat is the test entry: create session first, then send messages. Optionally pass `agent_id` to select the executing Agent resource.

## Chat APIs

- `POST /api/v1/chat/projects/{project_id}/sessions`
- `POST /api/v1/chat/sessions/{session_id}/messages`

## Runtime 节点 / Runtime Node

中文：
Runtime 会读取 Agent 资源中的：
- `model_provider`
- `model_name`
- `provider_profile`（如果模板/资源配置了该字段）
- `config.system_prompt`

然后路由到对应 Provider 执行。

如果 Agent 来源于默认模板：
- 模板定义保存在 `backend/app/core/default_resources.json`
- 用户在前端选择模板后，会创建成数据库中的项目资源
- 运行时仍然读取数据库中的资源配置执行，不直接执行 JSON 模板

English:
Runtime reads from Agent resource:
- `model_provider`
- `model_name`
- `provider_profile` (if configured on the template/resource)
- `config.system_prompt`

Then dispatches to the corresponding provider.

If the Agent comes from a default template:
- The template definition lives in `backend/app/core/default_resources.json`
- Selecting a template in the UI creates a project resource in the database
- Runtime still executes the DB resource, not the raw JSON template

## 代码位置 / Code References

- `backend/app/api/v1/chat.py`
- `backend/app/runtime/executor.py`
- `backend/app/runtime/providers.py`
- `backend/app/services/postgres_store.py`
