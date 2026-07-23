# Node 03: Chat and Runtime (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## Chat 节点 / Chat Node

Chat 是运行测试入口：先创建 session，再发送 message。发送消息时可传 `agent_id` 指定 Agent，也可传 `engine_type`、`provider_profile`、`temperature`、`max_iterations`、`mcp_ids` 做请求级覆盖。

## Chat APIs

- `POST /api/v1/chat/projects/{project_id}/sessions`
- `GET /api/v1/chat/projects/{project_id}/sessions`
- `GET /api/v1/chat/sessions/{session_id}/messages`
- `POST /api/v1/chat/sessions/{session_id}/messages`
- `GET /api/v1/chat/sessions/{session_id}/runs`
- `GET /api/v1/chat/runs/{run_id}/events`
- `GET /api/v1/chat/code-execution-audits`
- `GET /api/v1/chat/agents/{agent_id}/debug`

## Runtime 节点 / Runtime Node

Runtime 会读取 Agent 资源中的：

- `model_provider`
- `model_name`
- `provider_profile`
- `provider_connection_id`
- `config.system_prompt`
- `config.run_mode`
- `config.custom_code`
- `config.tool_ids` / `skill_ids` / `mcp_ids` / `knowledge_base_ids`

如果 Agent 来源于默认模板，用户在前端选择模板后会创建成数据库中的项目资源；运行时执行的是数据库资源配置，不直接执行 JSON 模板。

## Execution Modes / 执行模式

1. `llm` / legacy provider call
- 直接调用 OpenAI-compatible 或 localhost provider。
- 支持 `.env` provider profile 或项目级 Provider Connection。

2. `code`
- 执行 Agent `custom_code`。
- 可通过 `call_tool(...)` 调用关联 Tool。
- 可通过 `call_mcp(...)` 调用关联 MCP 工具。
- 返回 `{"use_llm": true}` 时可回退到 LLM。

3. `engine_type=react`
- 使用 ReAct thought/action/observation loop。
- 通过文本格式驱动工具选择，适合不支持 function calling 的 OpenAI-compatible 模型。
- 当前重点支持 MCP tools 和内置工具；Skill/Knowledge Base 的 ReAct 工具语义仍在演进。

## Runtime Timeline / 运行时间线

每次发送消息都会创建 `runtime_runs` 记录，并写入 `runtime_run_events`。当前事件覆盖：

- `runtime`: running/succeeded/failed。
- `agent`: 选中 Agent、provider、model、engine 信息。
- `code_execution`: code-mode 开始、完成、失败、审计信息。
- `tool` / `mcp`: Tool/MCP 调用摘要与 Workbench 标签。
- ReAct steps: thought/action/observation/final answer 以事件 payload 形式记录。

## Response Fields / 响应字段

`POST /api/v1/chat/sessions/{session_id}/messages` 返回：

- `run_id`: 本次运行 ID。
- `used_tools`: code-mode 调用过的 Tool 名称。
- `used_mcps`: code-mode 调用过的 MCP/tool 对。

## 代码位置 / Code References

- `backend/app/api/v1/chat.py`
- `backend/app/runtime/executor.py`
- `backend/app/runtime/llm_service.py`
- `backend/app/runtime/code_executor.py`
- `backend/app/runtime/agent_engine/react_agent.py`
- `backend/app/runtime/agent_engine/tool_manager.py`
- `backend/app/services/postgres_store.py`
