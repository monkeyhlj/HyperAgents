# Node 02: Resource and Registry (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## Resource 节点 / Resource Node

Resource 是统一抽象，当前支持：

- `agent`
- `workflow`
- `tool`
- `skill`
- `mcp`
- `knowledge_base`

资源字段包括 `kind`、`name`、`description`、`visibility`、`model_provider`、`model_name`、`provider_profile`、`provider_connection_id`、`config`。

## 默认模板 vs 数据库资源 / Default Templates vs Database Resources

- `backend/app/core/default_resources.json` 只保存默认模板。
- 默认模板用于前端展示可选项，用户选择后再创建为项目资源。
- 用户创建的资源落到数据库 `resources` 表。
- 默认模板不保存真实密钥，只保存模板参数和 `provider_profile`。

## 创建与读取规则 / Creation and Read Rules

- `GET /api/v1/resources/projects/{project_id}` 默认合并“默认模板 + 数据库资源”。
- 如只看数据库资源，传 `include_defaults=false`。
- `GET /api/v1/resources/defaults` 单独获取默认模板。
- `GET /api/v1/resources/mine` 获取当前用户拥有或可见的资源，并带 `project_name`。
- `POST /api/v1/resources/preview-chat` 用于保存前预览 Agent 配置。

## 资源接口 / Resource APIs

- `POST /api/v1/resources/projects/{project_id}`
- `GET /api/v1/resources/projects/{project_id}?kind=&visibility=&include_defaults=`
- `GET /api/v1/resources/defaults`
- `GET /api/v1/resources/mine`
- `GET /api/v1/resources/{resource_id}`
- `PATCH /api/v1/resources/{resource_id}`
- `DELETE /api/v1/resources/{resource_id}`
- `POST /api/v1/resources/preview-chat`

## 可见性 / Visibility

- `private`: 仅资源 owner 可见。
- `project`: 项目成员可见。
- `public`: 跨项目公开可发现。

## Provider 配置 / Provider Configuration

- `model_provider` 决定运行时客户端类型，例如 `openai` 或 `localhost`。
- `provider_profile` 决定读取哪组环境变量前缀，例如 `zhipu` -> `ZHIPU_API_KEY` / `ZHIPU_BASE_URL` / `ZHIPU_DEFAULT_MODEL`。
- `provider_connection_id` 指向项目级 Provider Connection，适合由用户在 UI 中填写 URL + API Key 后加密保存。

## Registry 节点 / Registry Node

Registry 是资源市场入口，目前限定三类：`mcp/tool/skill`。

### Registry APIs

- `POST /api/v1/registry/projects/{project_id}/{kind}`
- `GET /api/v1/registry/projects/{project_id}/{kind}?visibility=`
- `GET /api/v1/registry/public/{kind}`
- `POST /api/v1/registry/mcp/probe`

## 典型用途 / Typical Use

- 项目内共享 Tool、Skill 或 MCP。
- 把成熟 MCP 发布为 public 供其他项目复用。
- 保存前使用 MCP probe 验证 `streamable_http` endpoint。

## 代码位置 / Code References

- `backend/app/api/v1/resources.py`
- `backend/app/api/v1/registry.py`
- `backend/app/services/postgres_store.py`
- `backend/app/services/default_resource_store.py`
- `backend/app/schemas/resource.py`
- `backend/app/schemas/registry.py`
