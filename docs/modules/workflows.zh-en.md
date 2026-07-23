# Workflows Module Guide / Workflows 模块说明

状态 / Status: Resource management implemented; dedicated workflow runtime is not yet implemented.

## Purpose / 作用

中文：
用于管理工作流定义与流程编排资源。当前 Workflow 作为 `workflow` 资源被创建、编辑、查询和删除；专用 workflow runtime 尚未在后端形成独立执行接口。

English:
Manages workflow definitions and orchestration resources. Workflow is currently managed as a `workflow` resource; a dedicated workflow runtime API has not yet been implemented.

## Current Scope / 当前范围

1. Workflow 资源创建与编辑。
2. 与项目及其他资源的关系维护。
3. 通过 `config` 保存步骤、依赖、触发条件等编排元数据。

## Recommended Config Shape / 推荐配置结构

```json
{
  "trigger": "manual",
  "steps": [
    {
      "id": "triage",
      "type": "agent",
      "resource_name": "ops-agent"
    },
    {
      "id": "notify",
      "type": "tool",
      "resource_name": "send-ticket-update"
    }
  ],
  "edges": [
    {"from": "triage", "to": "notify"}
  ]
}
```

## API Mapping / API 对照

- `POST /api/v1/resources/projects/{project_id}` with `kind=workflow`: 创建 Workflow。
- `GET /api/v1/resources/projects/{project_id}?kind=workflow`: 查询项目 Workflow。
- `PATCH /api/v1/resources/{resource_id}`: 更新 Workflow。
- `DELETE /api/v1/resources/{resource_id}`: 删除 Workflow。

## Test Checklist / 测试清单

1. 创建 Workflow 并保存结构化 `config`。
2. 编辑步骤和依赖关系后重新打开确认未丢失。
3. 验证 workflow 资源的 private/project/public 可见性。
4. 在资源列表和项目详情页均可看到 Workflow。
5. 不要把 Workflow 文档描述成已经具备独立执行 API，直到后端实现相应 runtime。

## Notes / 备注

- 当前 Workflow 是“编排定义资源”，不是独立运行引擎。
- 真正可执行逻辑目前应放在 Agent、Tool、MCP 或后端 runtime 中。
- 若后续新增 workflow runtime，应同步更新本页、`reference/code-api-map.zh-en.md` 和 `reference/api-changelog.zh-en.md`。
