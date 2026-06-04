# PM Playbook (中文 + English)

导航 / Navigation: [角色总览](roles-overview.zh-en.md) | [架构路线](../reference/architecture-roadmap.zh-en.md)

## 1) 目标 / Goal

中文：
帮助产品侧快速理解当前能力边界、近期里程碑、验收标准，并将需求转化为可执行迭代。

English:
Help product stakeholders quickly understand capability boundaries, near-term milestones, acceptance criteria, and how to turn requirements into executable iterations.

## 2) 当前能力边界 / Current Capability Scope

1. 项目/成员权限闭环。
2. 资源注册与查询。
3. Workbench 会话调试。
4. Runtime Run Timeline 可观测。
5. Memory 重试支持队列或本地回退。

## 3) 近期里程碑 / Near-term Milestones

1. Runtime 事件扩展到 tool/mcp/memory。
2. Worker 任务中心与状态查询。
3. Run 指标化（耗时、token 使用）。

## 4) 需求提报模板 / Requirement Template

1. 业务目标（为什么做）。
2. 用户角色与场景。
3. 可验收结果（可观测、可测试）。
4. 风险与边界。
5. 上线策略与回滚要求。

## 5) 验收建议 / Acceptance Suggestions

1. 功能验证：走 testing-playbook 主链路。
2. 体验验证：重点看 Projects/Workbench。
3. 稳定性验证：至少观察一天运行错误率。
