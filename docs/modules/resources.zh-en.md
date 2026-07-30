# Resources Module Guide / Resources 模块说明

状态 / Status: Implemented and code-aligned.

## Purpose / 作用

中文：
用于统一管理各类资源（agent、workflow、tool、skill、mcp、knowledge_base）的创建、查询与维护。

English:
Provides unified creation, querying, and maintenance of resource types (agent, workflow, tool, skill, mcp, knowledge_base).

## Current Scope / 当前范围

1. 按类型管理资源。 / Manage resources by kind.
2. 资源归属项目与可见性控制。 / Control resource project ownership and visibility.
3. 资源编辑与删除。 / Edit and delete resources.
4. 默认资源模板读取。 / Load default resource templates.
5. 我的资源列表与项目资源列表。 / List owned resources and project resources.
6. Agent preview chat、Provider Connection、MCP probe 等资源相关辅助能力。 / Support resource-related helpers such as Agent preview chat, Provider Connection, and MCP probe.

## Resource Kinds / 资源类型

| Kind | Purpose |
| --- | --- |
| `agent` | Runtime 可执行 Agent，支持 llm/code 模式 / Runtime-executable Agent supporting llm/code modes |
| `workflow` | 工作流资源，目前以前端资源形态维护 / Workflow resource managed through frontend resource screens |
| `tool` | code-mode Agent 可调用的 Python Tool / Python Tool callable by code-mode Agents |
| `skill` | 场景能力说明与组合资源 / Scenario-specific instruction and composition resource |
| `mcp` | HTTP MCP server 连接配置 / HTTP MCP server connection configuration |
| `knowledge_base` | 知识库资源配置 / Knowledge base resource configuration |

## API Mapping / API 对照

- `GET /api/v1/resources/defaults`: 读取 `backend/app/core/default_resources.json` 中的默认模板。
- `GET /api/v1/resources/mine`: 查询当前用户可见或拥有的资源。
- `GET /api/v1/resources/projects/{project_id}`: 查询项目资源，支持 `kind`、`visibility`、`include_defaults`。
- `POST /api/v1/resources/projects/{project_id}`: 创建项目资源。
- `GET /api/v1/resources/{resource_id}`: 查看单个资源。
- `PATCH /api/v1/resources/{resource_id}`: 更新资源。
- `DELETE /api/v1/resources/{resource_id}`: 删除资源。
- `POST /api/v1/resources/preview-chat`: 对未保存或编辑中的 Agent 配置进行预览对话。

## Visibility Rules / 可见性规则

- `private`: 仅资源 owner 可见。
- `project`: 项目成员可见。
- `public`: 跨项目公开可发现。

## Test Checklist / 测试清单

1. 新增资源。 / Create a resource.
2. 编辑资源。 / Edit a resource.
3. 删除资源。 / Delete a resource.
4. 不同可见性下访问校验。 / Verify access under different visibility settings.
5. 默认 Agent 模板可展示并可创建为项目资源。 / Default Agent templates can be displayed and created as project resources.
6. `preview-chat` 可在保存前验证 Agent 配置。 / `preview-chat` can validate Agent configuration before saving.
7. `mine` 列表可按资源类型筛选。 / The `mine` list can be filtered by resource kind.

## Notes / 备注

- 默认模板只应保存模板和 profile，不保存真实密钥。 / Default templates should store templates and profiles only, never real secrets.
- Provider 密钥优先来自 `.env` 或项目级 Provider Connection。 / Provider secrets should come from `.env` or project-level Provider Connections.
- MCP、Tool、Skill、Knowledge Base 的详细用法分别见对应模块文档。 / See each module guide for detailed MCP, Tool, Skill, and Knowledge Base usage.
