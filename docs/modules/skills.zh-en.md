# Skills Module Guide / Skills 模块说明

状态 / Status: Resource model implemented; runtime semantics are intentionally lightweight.

## Purpose / 作用

中文：
用于管理可复用技能定义，给 Agent 提供行为模板、操作说明或能力片段。当前 Skill 以资源形式保存，并可在 Agent 配置中关联。

English:
Manages reusable skill definitions that provide behavior templates, operating instructions, or capability snippets for agents. Skills are currently stored as resources and can be associated with Agents.

## Current Scope / 当前范围

1. Skill 资源创建、编辑、删除、查询。
2. Skill 与 Agent 的配置关联。
3. 通过 `config` 保存结构化技能元数据。

## Recommended Config Shape / 推荐配置结构

```json
{
  "category": "ops",
  "instructions": "Summarize alerts and propose next actions.",
  "inputs": ["alert_payload", "service_name"],
  "outputs": ["summary", "recommended_actions"],
  "tags": ["incident", "triage"]
}
```

## API Mapping / API 对照

- `POST /api/v1/resources/projects/{project_id}` with `kind=skill`: 创建 Skill。
- `GET /api/v1/resources/projects/{project_id}?kind=skill`: 查询项目 Skill。
- `PATCH /api/v1/resources/{resource_id}`: 更新 Skill。
- `DELETE /api/v1/resources/{resource_id}`: 删除 Skill。
- `POST /api/v1/registry/projects/{project_id}/skill`: 注册项目级 Skill。
- `GET /api/v1/registry/public/skill`: 浏览 public Skill。

## Test Checklist / 测试清单

1. 创建 Skill，并写入说明与结构化 `config`。
2. 在 Agent 中关联 Skill。
3. 保存 Agent 后重新打开，确认关联未丢失。
4. 验证 private/project/public 可见性。
5. 如需跨项目复用，将 Skill 设为 public 并通过 registry 浏览。

## Notes / 备注

- 当前 Skill 不直接执行代码；可执行逻辑应放到 Tool、MCP 或 Agent code mode。
- Skill 更适合保存可复用说明、流程、prompt 片段和能力元数据。
