# PM Playbook (中文 + English)

导航 / Navigation: [角色总览](roles-overview.zh-en.md) | [架构路线](../reference/architecture-roadmap.zh-en.md)

## 1) 目标 / Goal

中文：
帮助产品侧快速理解当前能力边界、近期里程碑、验收标准，并将需求转化为可执行迭代。

English:
Help product stakeholders quickly understand capability boundaries, near-term milestones, acceptance criteria, and how to turn requirements into executable iterations.

## 2) 当前能力边界 / Current Capability Scope

1. 项目/成员权限闭环。 / Closed-loop project and member permissions.
2. 资源创建、编辑、删除、默认模板和我的资源列表。 / Resource create/edit/delete, default templates, and owned-resource lists.
3. Provider Connection：项目级 URL + API Key 模型连接、模型加载、连接测试、加密保存。 / Project-level URL + API Key model connections, model loading, connection testing, and encrypted storage.
4. MCP：HTTP endpoint 配置、probe、Agent code-mode 调用。 / HTTP endpoint configuration, probe, and Agent code-mode calls.
5. Workbench 会话调试、历史会话、Run Timeline、事件查看。 / Workbench session testing, session history, Run Timeline, and event viewing.
6. Agent：LLM 模式、code 模式、可选 ReAct engine。 / Agent LLM mode, code mode, and optional ReAct engine.
7. Memory：写入、查询、语义检索、embedding retry，支持队列或本地回退。 / Memory write/query, semantic retrieval, embedding retry, and queue/local fallback.

## 3) 当前未完成边界 / Not Yet Complete

1. Workflow 目前是资源定义管理，尚无独立 workflow runtime。 / Workflow was originally resource-definition management only; check the current Workflow module for runtime status.
2. Worker 尚无任务中心 UI/API。 / Worker has no dedicated task-center UI/API yet.
3. Run 尚未沉淀 token usage、latency breakdown 等指标字段。 / Runs do not yet persist metrics such as token usage or latency breakdown.
4. ReAct 中 Skill/Knowledge Base 工具语义仍在演进。 / Skill and Knowledge Base tool semantics in ReAct are still evolving.
5. Public registry 缺少审核、版本和发布流程。 / Public registry lacks review, versioning, and release workflows.

## 4) 近期里程碑 / Near-term Milestones

1. Runtime 指标化（耗时、token 使用、provider/model metadata）。
2. Worker 任务中心与状态查询。
3. Workflow runtime MVP。 / Workflow runtime MVP.
4. Registry 治理：版本、审核、发布状态。

## 5) 需求提报模板 / Requirement Template

1. 业务目标（为什么做）。 / Business goal: why this should be built.
2. 用户角色与场景。 / User roles and scenarios.
3. 可验收结果（可观测、可测试）。 / Acceptable outcomes that are observable and testable.
4. 数据和权限边界。 / Data and permission boundaries.
5. 风险与上线/回滚策略。 / Risks plus release and rollback strategy.

## 6) 验收建议 / Acceptance Suggestions

1. 功能验证：走 testing-playbook 主链路。
2. 体验验证：重点看 Projects/Resources/Workbench。
3. 稳定性验证：观察 run failed、provider test failed、worker failed。
4. 文档验证：需求涉及新 API 时，确认 code-api-map 与模块文档同步。
