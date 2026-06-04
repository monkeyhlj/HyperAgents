# Node 02: Resource and Registry (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## Resource 节点 / Resource Node

中文：
Resource 是统一抽象，支持：
- agent
- workflow
- tool
- skill
- mcp
- knowledge_base

English:
Resource is the unified abstraction with these kinds:
- agent
- workflow
- tool
- skill
- mcp
- knowledge_base

### 默认模板 vs 数据库资源 / Default Templates vs Database Resources

中文：
- `backend/app/core/default_resources.json` 只保存“默认模板”。
- 默认模板用于前端展示可选项，用户选择后再创建为项目资源。
- 用户自己创建的资源会落到数据库 `resources` 表。
- 默认模板不保存真实密钥，只保存模板参数和 `provider_profile`。

English:
- `backend/app/core/default_resources.json` stores default templates only.
- Default templates are shown in the UI as selectable options, then created into project resources.
- User-created resources are persisted in the database `resources` table.
- Default templates do not store real secrets; they only store template parameters and `provider_profile`.

### 创建与读取规则 / Creation and Read Rules

中文：
- `GET /api/v1/resources/projects/{project_id}` 默认会合并“默认模板 + 数据库资源”。
- 如果只想看数据库资源，可传 `include_defaults=false`。
- `GET /api/v1/resources/defaults` 可单独获取默认模板列表。

English:
- `GET /api/v1/resources/projects/{project_id}` merges default templates and DB resources by default.
- To query DB resources only, pass `include_defaults=false`.
- `GET /api/v1/resources/defaults` returns default templates only.

### 资源接口 / Resource APIs

- `POST /api/v1/resources/projects/{project_id}`
- `GET /api/v1/resources/projects/{project_id}?kind=&visibility=`

### 可见性 / Visibility

- `private`: 仅 owner
- `project`: 项目成员可见
- `public`: 所有人可见

### provider_profile 约定 / provider_profile Convention

中文：
- `model_provider` 决定走哪个运行时客户端类型，例如 `openai` 或 `localhost`。
- `provider_profile` 决定读取哪一组环境变量前缀，例如 `zhipu` -> `ZHIPU_API_KEY` / `ZHIPU_BASE_URL` / `ZHIPU_DEFAULT_MODEL`。
- 新增 provider 时，推荐新增一个默认模板，然后补对应前缀的 `.env` 变量。

English:
- `model_provider` decides which runtime client type is used, such as `openai` or `localhost`.
- `provider_profile` decides which env-prefix to read, for example `zhipu` -> `ZHIPU_API_KEY` / `ZHIPU_BASE_URL` / `ZHIPU_DEFAULT_MODEL`.
- When adding a new provider, prefer adding a new default template first, then add the matching `.env` variables.

## Registry 节点 / Registry Node

中文：
Registry 是资源市场入口，目前限定三类：`mcp/tool/skill`。

English:
Registry is the marketplace-like entry. It currently supports three kinds: `mcp/tool/skill`.

### Registry APIs

- `POST /api/v1/registry/projects/{project_id}/{kind}`
- `GET /api/v1/registry/projects/{project_id}/{kind}?visibility=`
- `GET /api/v1/registry/public/{kind}`

### 典型用途 / Typical Use

中文：
- 项目内共享一个 Tool 或 Skill
- 把成熟 MCP 发布为 public 供其他项目复用

English:
- Share a Tool or Skill inside a project
- Publish stable MCP as public for reuse across projects

## 代码位置 / Code References

- `backend/app/api/v1/resources.py`
- `backend/app/api/v1/registry.py`
- `backend/app/services/postgres_store.py`
- `backend/app/schemas/resource.py`
- `backend/app/schemas/registry.py`
