# Workbench Module Guide / Workbench 模块说明

状态 / Status: Implemented and code-aligned.

## Purpose / 作用

中文：
用于会话调试、消息收发、运行时间线查看与运行事件分析。

English:
Provides session debugging, message exchange, runtime timeline viewing, and run-event analysis.

## Current Scope / 当前范围

1. 项目选择与会话创建。
2. Agent 选择与消息发送。
3. Run Timeline 与 Events 查看。
4. 历史会话与历史消息加载。
5. Tool/MCP 调用标签展示。

## API Mapping / API 对照

- `POST /api/v1/chat/projects/{project_id}/sessions`: 创建会话。
- `GET /api/v1/chat/projects/{project_id}/sessions`: 加载项目会话。
- `GET /api/v1/chat/sessions/{session_id}/messages`: 加载历史消息。
- `POST /api/v1/chat/sessions/{session_id}/messages`: 发送消息并触发 runtime。
- `GET /api/v1/chat/sessions/{session_id}/runs`: 查看会话 run 列表。
- `GET /api/v1/chat/runs/{run_id}/events`: 查看 run 事件。
- `GET /api/v1/chat/code-execution-audits`: 查看 code-mode 执行审计。

## Runtime Timeline / 运行时间线

每次发送消息后，后端会创建 Runtime Run，并记录阶段事件。当前事件覆盖：

- runtime start/succeeded/failed。
- agent 选择、模型与执行信息。
- code-mode Tool/MCP 调用结果。
- 异常时的错误信息。

## Test Checklist / 测试清单

1. 新建会话。
2. 发送消息。
3. 查看 run 与 events。
4. 切换历史会话后消息仍可加载。
5. code-mode Agent 调用 Tool 时显示 tool 标签。
6. code-mode Agent 调用 MCP 时显示 mcp/tool 标签。
7. 模型调用失败时 run 状态为 failed 且 events 中有错误原因。

## Notes / 备注

- Workbench 不负责创建资源；资源应先在 Resources 或 Project Detail 中创建。
- Agent 列表来自当前项目下的 `kind=agent` 资源。
- Timeline 数据由后端 runtime 自动生成，不需要单独启动进程。
