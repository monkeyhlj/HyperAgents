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

### 资源接口 / Resource APIs

- `POST /api/v1/resources/projects/{project_id}`
- `GET /api/v1/resources/projects/{project_id}?kind=&visibility=`

### 可见性 / Visibility

- `private`: 仅 owner
- `project`: 项目成员可见
- `public`: 所有人可见

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
