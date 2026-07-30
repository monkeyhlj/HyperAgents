# Workflow Implementation Plan

**Language:** 中文为主，保留英文术语以便和代码、API、配置结构对应。

---

<a id="中文"></a>

## 中文

### 1. 背景与目标

当前 HyperAgents 已支持 `workflow` 作为资源类型，并且前端已有 Workflows 菜单、列表、创建和编辑入口。但从代码现状看，Workflow 目前主要还是资源壳：可以作为 Resource 创建/编辑，但缺少真正的 Workflow Run、Step Execution、DAG 执行引擎和测试界面。

目标是基于 `docs/design/knowledge-skills-workflows-design.zh-en.md` 的 Workflow 章节，把 Workflow 做成可用的多 Agent 编排系统。

核心目标：

| 能力 | 目标 |
|------|------|
| Definition | 支持 JSON/YAML 定义步骤、Agent、输入模板、路由规则 |
| Validation | 保存前验证所有 Agent 在同一项目、步骤引用合法、无环 |
| Run | 手动运行 Workflow |
| Step Execution | 每一步调用指定 Agent，并保存输入、输出、状态、耗时 |
| Routing | 根据步骤输出选择下一步 |
| Observability | 前端展示运行历史、步骤状态、中间输出和错误 |
| Integration | 每个步骤复用现有 Agent 能力，包括 Tools、MCPs、Knowledge、Skills |

---

### 2. 当前现状

已具备：

1. `ResourceKind.WORKFLOW` 已存在。
2. 前端路由已有：
   - `/workflows`
   - `/workflows/create`
   - `/workflows/:resourceId/edit`
3. Workflow 使用通用 `ResourceOwnedListView.vue` 展示。
4. Workflow 创建/编辑复用 `ResourceCreateView.vue` 的 Config JSON。
5. Memory 模型中已有 `workflow_run_id` 字段，可为后续 Execution Memory 留接口。

缺失：

1. 后端没有 `workflow_runs` 表。
2. 后端没有 `workflow_step_executions` 表。
3. 没有 Workflow API：run、runs、run detail。
4. 没有 Workflow Engine。
5. 没有模板变量替换系统。
6. 没有条件路由系统。
7. 前端没有 Workflow 测试/运行/Trace 页面。

---

### 3. 建议定义格式

建议先用 JSON 作为主格式，YAML 作为后续增强。原因是当前前端已有 JSON editor，后端也更容易校验。

最小定义：

```json
{
  "version": "1.0.0",
  "status": "draft",
  "timeout_seconds": 300,
  "max_retries": 1,
  "steps": [
    {
      "id": "classify",
      "name": "Classify issue",
      "agent_id": "agent-id-1",
      "input": {
        "text": "{{ input.customer_question }}"
      },
      "output_mode": "text",
      "routing": [
        {
          "condition": "output.priority == 'high'",
          "next": "escalate"
        },
        {
          "condition": "output.issue_type == 'technical'",
          "next": "resolve_technical"
        },
        {
          "default": true,
          "next": "resolve_general"
        }
      ]
    },
    {
      "id": "resolve_general",
      "agent_id": "agent-id-2",
      "input": {
        "text": "Question: {{ input.customer_question }}\nClassification: {{ steps.classify.output }}"
      }
    }
  ],
  "output": {
    "summary": "{{ last.output }}",
    "steps": "{{ steps }}"
  }
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `version` | Workflow 定义版本 |
| `status` | draft/active/paused |
| `timeout_seconds` | 全局超时 |
| `max_retries` | 默认重试次数 |
| `steps[].id` | 步骤唯一 ID |
| `steps[].agent_id` | 同项目内 Agent ID |
| `steps[].input` | 输入模板 |
| `steps[].routing` | 条件路由 |
| `steps[].on_error` | 错误路由 |
| `output` | 最终输出模板 |

---

### 4. 后端实现方案

#### Phase 1：数据库与 Schema

新增模型：

```python
class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    id: str
    workflow_id: str
    project_id: str
    triggered_by: str
    trigger_type: str
    input_data: dict
    status: str
    output_data: dict | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None

class WorkflowStepExecutionModel(Base):
    __tablename__ = "workflow_step_executions"

    id: str
    workflow_run_id: str
    step_id: str
    step_name: str | None
    agent_id: str
    input_data: dict
    output_data: dict | None
    status: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    order_index: int
```

新增 Pydantic schema：

- `WorkflowRunRequest`
- `WorkflowRunRecord`
- `WorkflowStepExecutionRecord`
- `WorkflowRunDetail`
- `WorkflowDefinitionValidationResult`

验收标准：

- Alembic migration 可执行。
- 能保存 run 和 step execution。
- 删除 workflow resource 时，历史 run 是否保留需要明确策略。建议先 CASCADE 删除，后续加归档。

---

#### Phase 2：Workflow Definition Validator

新增模块：

```text
backend/app/runtime/workflow/definition.py
```

校验内容：

1. `steps` 必须非空。
2. 每个 step id 唯一。
3. 每个 `agent_id` 存在且属于同一 project。
4. routing 的 `next` 必须引用存在的 step。
5. `on_error` 必须引用存在的 step。
6. 检测循环。P0 阶段建议默认禁止循环。
7. 检查模板变量基础语法。
8. 检查至少存在一个起始步骤。

起始步骤规则：

- P0 简化：`steps[0]` 为起始步骤。
- P1 增强：支持 `start_step` 字段。

验收标准：

- 保存 Workflow 时可提示定义错误。
- Run 前强制验证。

---

#### Phase 3：模板变量系统

新增模块：

```text
backend/app/runtime/workflow/template.py
```

支持变量：

| 变量 | 示例 |
|------|------|
| `input` | `{{ input.customer_question }}` |
| `steps` | `{{ steps.classify.output }}` |
| `last` | `{{ last.output }}` |
| `run` | `{{ run.id }}` |

P0 实现建议：

- 使用安全的点路径解析，不使用 Python `eval`。
- 模板只支持 `{{ path.to.value }}`。
- 如果值是对象，转 JSON 字符串。

P1 再支持：

- `||` fallback。
- 简单 filter，例如 `json`、`text`。

验收标准：

- 能把上一步输出拼到下一步输入。
- 不允许执行任意代码。

---

#### Phase 4：条件路由系统

新增模块：

```text
backend/app/runtime/workflow/routing.py
```

P0 条件表达式建议：

```text
output.priority == 'high'
output.issue_type == 'technical'
output.score >= 0.8
'tag-a' in output.tags
```

安全策略：

- 不使用 Python `eval`。
- 自己解析有限操作符：`==`、`!=`、`>`、`>=`、`<`、`<=`、`in`、`not in`。
- 左右两侧只允许字面量或点路径。

P1 可替换为 JsonLogic。

验收标准：

- 多条 routing 按顺序判断。
- 命中第一条后跳转。
- `default: true` 作为兜底。
- 无路由时工作流结束或进入顺序下一步，需固定规则。建议 P0：无 routing 则顺序执行下一步。

---

#### Phase 5：Workflow Engine

新增模块：

```text
backend/app/runtime/workflow/engine.py
```

核心类：

```python
class WorkflowEngine:
    async def run_workflow(
        self,
        db,
        workflow_resource,
        input_data,
        user_id,
    ) -> WorkflowRunResult:
        ...
```

P0 执行策略：顺序 + 条件跳转。

流程：

1. 创建 `WorkflowRunModel`，状态 running。
2. 加载 workflow definition。
3. 校验 definition。
4. 从起始 step 开始。
5. 渲染 step input。
6. 创建 `WorkflowStepExecutionModel`。
7. 调用目标 Agent。
8. 保存 step output。
9. 根据 routing 决定下一步。
10. 渲染最终 output。
11. 标记 run completed/failed。

Agent 调用建议：

- P0：抽出 chat.py 中“运行一个 Agent”的核心逻辑为 service，Workflow 复用。
- 不建议 Workflow 直接 HTTP 调用自身 chat API，避免认证、事务和嵌套请求复杂化。

建议新增：

```text
backend/app/runtime/agent_runner.py
```

用于：

- Workbench chat 调用 Agent。
- Workflow step 调用 Agent。
- 后续 scheduled/event trigger 调用 Agent。

验收标准：

- 一个 2 步串行 Workflow 可以跑通。
- 每一步能使用该 Agent 绑定的 Tools/MCPs/Knowledge/Skills。
- 前端能查看每一步输入输出。

---

### 5. API 设计

新增 router：

```text
backend/app/api/v1/workflows.py
```

API：

```text
POST   /api/v1/workflows/{workflow_id}/validate
POST   /api/v1/workflows/{workflow_id}/run
GET    /api/v1/workflows/{workflow_id}/runs
GET    /api/v1/workflows/{workflow_id}/runs/{run_id}
GET    /api/v1/workflows/runs/{run_id}/events    # 可选，类似 chat runs events
```

请求示例：

```json
{
  "input_data": {
    "customer_question": "我的订单一直没有发货怎么办？"
  },
  "trigger_type": "manual"
}
```

返回示例：

```json
{
  "run_id": "...",
  "status": "completed",
  "output_data": {
    "summary": "..."
  },
  "steps": [
    {
      "step_id": "classify",
      "status": "completed",
      "agent_id": "...",
      "input_data": {},
      "output_data": {},
      "duration_ms": 1200
    }
  ]
}
```

---

### 6. 前端实现方案

#### Phase 1：JSON 编辑 + 测试运行

先不做复杂可视化 DAG，避免范围过大。

在 Workflow 创建/编辑页中增加：

1. Workflow Definition JSON 编辑器。
2. Validate 按钮。
3. Test Run 输入区。
4. Run Result 面板。
5. Step Timeline。

现有 `ResourceCreateView.vue` 可以先复用 Config JSON，但建议对 `kind === workflow` 做专门 UI：

- Project 选择。
- Name/Description。
- Allowed Agents 多选。
- Definition JSON。
- Status draft/active。
- Timeout/max retries。

#### Phase 2：Workflow Detail 页面

新增页面：

```text
frontend/src/views/workflows/WorkflowDetailView.vue
```

展示：

- Workflow 基本信息。
- Definition 只读或编辑入口。
- 手动运行表单。
- Runs 历史列表。
- Run detail 抽屉或详情页。
- 每步 input/output/error。

#### Phase 3：可视化 DAG 编辑器

后续再上。

候选方案：

| 方案 | 优点 | 缺点 |
|------|------|------|
| Vue Flow | 适合节点图编辑 | 需要新增依赖 |
| Vis.js | 简单图展示 | 编辑体验一般 |
| 自研简单 DAG UI | 可控 | 开发成本较高 |

建议先做只读 DAG 可视化，再做拖拽编辑。

---

### 7. 实施顺序建议

#### P0：可运行

1. 新增 DB models + migration。
2. 新增 workflow schemas。
3. 新增 definition validator。
4. 新增 template renderer。
5. 新增 WorkflowEngine 顺序执行。
6. 新增 `/workflows/{id}/run` API。
7. 前端增加 Test Run 面板。

验收：

- 能创建一个两步 Workflow。
- 第一步 Agent 输出进入第二步 Agent 输入。
- 能查看每步运行记录。

#### P1：可编排

1. 条件路由。
2. on_error 路由。
3. retry。
4. timeout。
5. Run history/detail 页面。
6. Workflow status：draft/active/paused。

验收：

- 根据分类 Agent 输出走不同路径。
- 某一步失败可以进入 error handler step。

#### P2：可视化和高级能力

1. DAG 可视化编辑。
2. 并行执行。
3. Human in the Loop。
4. 定时触发。
5. 版本管理。
6. A/B 测试。
7. Workflow 级成本统计。

---

### 8. 与 Agent/Skill/Knowledge/MCP 的集成建议

Workflow Step 不应该重新实现 Agent 能力，而应该调用统一 Agent Runner。

推荐架构：

```text
Workbench Chat ─┐
                ├── AgentRunner ── Tools
Workflow Step ──┘                 ├── MCPs
                                  ├── Knowledge
                                  └── Skills
```

这样可以保证：

- Workbench 和 Workflow 的 Agent 行为一致。
- Skills 改善后，Workflow 自动受益。
- Knowledge RAG 和 MCP 调用不用重复写。
- Trace 可以统一。

---

### 9. 风险与注意事项

| 风险 | 说明 | 建议 |
|------|------|------|
| 无限循环 | 条件路由可能形成环 | P0 禁止循环，P2 再支持循环并限制次数 |
| Agent 输出不结构化 | 条件路由依赖字段 | 支持 output parser，必要时要求 JSON 输出 |
| 多 Agent 成本高 | Workflow 会多次调用模型 | 每个 run 记录 token/cost，后续加预算 |
| 事务过长 | Workflow 运行时间较长 | 每步单独提交状态，不持有长事务 |
| 并发复杂 | 并行 DAG 容易复杂 | P0/P1 先串行，P2 再并行 |
| Skill 不稳定 | Step 内 Skill 执行失败影响 Workflow | 先补强 Skill Runtime，再做复杂 Workflow |

---

### 10. 推荐下一步

建议先做两个基础重构：

1. 抽出 `AgentRunner`，让 Workbench chat 和 Workflow step 共用。
2. 补强 `SkillTool`，让 AgentRunner 能真正调用 Skill。

然后再进入 Workflow P0。这样 Workflow 不会成为另一套平行 runtime，而是复用已经打通的 Agent 能力。
## English Companion Summary

This design note explains how Workflow should evolve from a simple `workflow` Resource into an executable multi-Agent orchestration system.

Key goals:

1. Define workflow steps, Agents, input templates, routing rules, and final output mapping in JSON first, with YAML as a possible future enhancement.
2. Validate definitions before saving or running: all referenced Agents must be accessible in the same Project, step references must be valid, and cyclic graphs should be rejected in the MVP.
3. Add runtime tables for workflow runs and step executions so every run, step input, step output, status, duration, and error can be inspected later.
4. Implement a Workflow Engine that can render templates, call existing Agents, route by step output, and collect final output.
5. Add a frontend test page with run history, step trace, intermediate outputs, and errors.
6. Reuse the existing Agent runtime so Workflow steps automatically benefit from Tools, MCPs, Knowledge, and Skills already bound to each Agent.

Implementation status note:

The current codebase has already implemented the core Workflow runtime, visual canvas authoring, run API, run history, and step trace. Treat this design file as a historical implementation plan; use `docs/modules/workflows.zh-en.md` and `docs/reference/code-api-map.zh-en.md` for current behavior.
