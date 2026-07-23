# Resources Module Guide / Resources 模块说明

状态 / Status: Implemented and code-aligned.

## Purpose / 作用

中文：
用于统一管理各类资源（agent、workflow、tool、skill、mcp、knowledge_base）的创建、查询与维护。

English:
Provides unified creation, querying, and maintenance of resource types (agent, workflow, tool, skill, mcp, knowledge_base).

## Current Scope / 当前范围

1. 按类型管理资源。
2. 资源归属项目与可见性控制。
3. 资源编辑与删除。
4. 默认资源模板读取。
5. 我的资源列表与项目资源列表。
6. Agent preview chat、Provider Connection、MCP probe 等资源相关辅助能力。

## Resource Kinds / 资源类型

| Kind | Purpose |
| --- | --- |
| `agent` | Runtime 可执行 Agent，支持 llm/code 模式 |
| `workflow` | 工作流资源，目前以前端资源形态维护 |
| `tool` | code-mode Agent 可调用的 Python Tool |
| `skill` | 场景能力说明与组合资源 |
| `mcp` | HTTP MCP server 连接配置 |
| `knowledge_base` | 知识库资源配置 |

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

1. 新增资源。
2. 编辑资源。
3. 删除资源。
4. 不同可见性下访问校验。
5. 默认 Agent 模板可展示并可创建为项目资源。
6. `preview-chat` 可在保存前验证 Agent 配置。
7. `mine` 列表可按资源类型筛选。

## Notes / 备注

- 默认模板只应保存模板和 profile，不保存真实密钥。
- Provider 密钥优先来自 `.env` 或项目级 Provider Connection。
- MCP、Tool、Skill、Knowledge Base 的详细用法分别见对应模块文档。
