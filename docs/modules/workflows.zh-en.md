# Workflows Module Guide / Workflows 模块说明

状态 / Status: Workflow resource management, visual canvas authoring, runtime execution, run history, and step trace are implemented.

## Purpose / 作用

中文：
Workflow 用于把同一个 Project 内的多个 Agent 编排成可执行流程。它适合内容生产、审核复检、数据分析、客服分流、自动化 SOP 等“多步骤、多角色、可追踪”的任务。

English:
Workflows orchestrate multiple Agents inside the same Project into an executable flow. They are useful for multi-step, multi-role, traceable processes such as content production, review, analysis, triage, and SOP automation.

## Current Scope / 当前范围

1. Workflow 作为 `kind=workflow` 的 Resource 创建、编辑、查询、删除。 / Workflow is created, edited, queried, and deleted as a `kind=workflow` Resource.
2. Create/Edit 页面提供图形化 Canvas：添加节点、分支、汇合节点，点击节点编辑右侧属性。 / The Create/Edit page provides a visual canvas for adding nodes, branches, join nodes, and editing selected node properties on the right.
3. Canvas 上的节点和连线会同步生成 Workflow Definition JSON。 / Canvas nodes and edges are synchronized into Workflow Definition JSON.
4. 后端支持 Definition 校验、手动运行、Run History 查询和 Step Trace 查询。 / The backend supports definition validation, manual runs, run history queries, and step trace queries.
5. Workflow Detail 页面提供对话式测试入口，并保留最近页面状态。 / The Workflow Detail page provides a chat-like test entry and keeps recent page state.
6. 每次运行写入 `workflow_runs`，每个步骤写入 `workflow_step_executions`。 / Each run is written to `workflow_runs`, and each step is written to `workflow_step_executions`.

## Definition Shape / 定义结构

```json
{
  "version": "1.0.0",
  "status": "draft",
  "timeout_seconds": 300,
  "max_retries": 0,
  "steps": [
    {
      "id": "planning",
      "name": "策划 Agent",
      "agent_id": "agent-id-1",
      "input": { "text": "{{ input.task }}" },
      "output_mode": "text",
      "next": ["copy", "visual"]
    },
    {
      "id": "copy",
      "name": "文案 Agent",
      "agent_id": "agent-id-2",
      "input": { "text": "基于策划结果写逐字稿：{{ steps.planning.output }}" },
      "depends_on": ["planning"],
      "next": ["review"]
    },
    {
      "id": "visual",
      "name": "视觉 Agent",
      "agent_id": "agent-id-3",
      "input": { "text": "基于策划结果写分镜：{{ steps.planning.output }}" },
      "depends_on": ["planning"],
      "next": ["review"]
    },
    {
      "id": "review",
      "name": "审核 Agent",
      "agent_id": "agent-id-1",
      "input": {
        "text": "合并并审校：\n文案：{{ steps.copy.output }}\n视觉：{{ steps.visual.output }}"
      },
      "depends_on": ["copy", "visual"],
      "output_mode": "text"
    }
  ],
  "output": {
    "summary": "{{ last.output }}",
    "steps": "{{ steps }}"
  }
}
```

## How To Create / 如何创建

1. 打开 `Workflows -> Create Workflow`。 / Open `Workflows -> Create Workflow`.
2. 选择 Project，填写 Name、Visibility 和 Description。 / Select a Project and fill in Name, Visibility, and Description.
3. 在 Workflow Canvas 中添加节点。 / Add nodes in the Workflow Canvas.
4. 点击节点，在右侧选择 Agent、编辑 Input Template、Output Mode。 / Click a node, then choose its Agent and edit Input Template and Output Mode on the right.
5. 需要分支时，从节点 handle 拖线到其它节点，或使用 `Add Branch`。 / To branch, drag from a node handle to another node or use `Add Branch`.
6. 需要合并时使用 `Add Join Node`，并让多个上游节点连到它。 / To merge branches, use `Add Join Node` and connect multiple upstream nodes to it.
7. 检查下方 `Workflow Definition JSON` 是否随 Canvas 同步变化。 / Check that `Workflow Definition JSON` below updates with the Canvas.
8. 保存后回到 Workflows 列表，点击 `Test` 进入测试页面。 / After saving, return to the Workflows list and click `Test` to open the test page.

## How To Test / 如何测试

1. 在 Workflow Detail 页面输入任务，例如： / Enter an input task on the Workflow Detail page, for example:

```json
{
  "task": "做一个关于如何养成阅读习惯的1分钟短视频"
}
```

2. 点击 Run。 / Click Run.
3. 左侧对话区域会显示运行中状态和最终 Markdown 结果。 / The left chat area shows the running state and the final Markdown result.
4. 右侧 Run History 展示历史运行；点击一条 completed/failed 记录可查看对应输出。 / Run History on the right shows past runs; click a completed/failed row to view its output.
5. Step Trace 用于排查每个节点的输入、输出、耗时和错误。 / Step Trace helps inspect each node input, output, duration, and error.

## API Mapping / API 对照

- `POST /api/v1/resources/projects/{project_id}` with `kind=workflow`: 创建 Workflow。
- `GET /api/v1/resources/projects/{project_id}?kind=workflow`: 查询项目 Workflow。
- `PATCH /api/v1/resources/{resource_id}`: 更新 Workflow。
- `DELETE /api/v1/resources/{resource_id}`: 删除 Workflow。
- `POST /api/v1/workflows/{workflow_id}/validate`: 校验定义。
- `POST /api/v1/workflows/{workflow_id}/run`: 手动运行。
- `GET /api/v1/workflows/{workflow_id}/runs`: 查询运行历史。
- `GET /api/v1/workflows/{workflow_id}/runs/{run_id}`: 查询运行详情和步骤记录。

## Test Checklist / 测试清单

1. 创建一个单节点 Workflow，确认 validate 成功。
2. 创建一个分支 + 汇合 Workflow，确认多个上游输出能进入审核节点。
3. 运行完成后刷新页面，确认 Run History 仍能加载。
4. 点击历史记录，确认左侧输出和右侧 Step Trace 同步切换。
5. 修改 Canvas 后保存，再重新进入 Edit 页面，确认节点、连线和 JSON 未丢失。
6. 删除关联 Agent 前，应先检查 Workflow 是否依赖该 Agent。

## Notes / 备注

- Workflow 只允许编排同 Project 内可访问的 Agent。 / A Workflow can only orchestrate accessible Agents in the same Project.
- `next` 表示下游节点，`depends_on` 表示上游依赖；Canvas 会尽量双向同步。 / `next` means downstream nodes, and `depends_on` means upstream dependencies; the Canvas keeps them synchronized as much as possible.
- 分支当前以 DAG 方式执行，适合明确流程，不适合无限循环或长时间异步任务。 / Branches currently run as a DAG, which fits explicit flows but not infinite loops or long-lived async tasks.
- Step Trace 是调试入口，不是最终用户输出；最终输出优先在左侧对话区域以 Markdown 展示。 / Step Trace is for debugging, not final user output; final output is shown first in the left chat area as Markdown.