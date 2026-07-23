# HyperAgents Documentation

欢迎来到 HyperAgents 文档站。

Welcome to the HyperAgents documentation site.

这里提供从快速上手、角色阅读、模块能力、架构节点到测试、运维和外部接入的完整路径。

This site provides a complete path from quick start, role-based reading, module guides, architecture nodes, testing, operations, and external integration.

## Recommended Path

1. [Quick Start](guides/quick-start.zh-en.md)
2. [Code and API Map](reference/code-api-map.zh-en.md)
3. [Role-based Reading Guide](roles/roles-overview.zh-en.md)
4. [Frontend Guide](guides/frontend-guide.zh-en.md)
5. [Agent Authoring Guide](modules/agents.zh-en.md)
6. [Runtime Run and Worker Guide](guides/runtime-run-worker.zh-en.md)
7. [Testing Playbook](guides/testing-playbook.zh-en.md)
8. [Deployment and Operations Guide](operations/deployment-operations.zh-en.md)
9. [External Resources Integration](guides/external-resources-integration.zh-en.md)
10. [Architecture Roadmap](reference/architecture-roadmap.zh-en.md)

## Module Docs

1. [Projects](modules/projects.zh-en.md)
2. [Resources](modules/resources.zh-en.md)
3. [Agents](modules/agents.zh-en.md)
4. [Tools](modules/tools.zh-en.md)
5. [Skills](modules/skills.zh-en.md)
6. [MCPs](modules/mcps.zh-en.md)
7. [Knowledge](modules/knowledge.zh-en.md)
8. [Workflows](modules/workflows.zh-en.md)
9. [Workbench](modules/workbench.zh-en.md)

## Architecture Nodes

1. [Node 01: Project and Members](nodes/01-project-and-members.zh-en.md)
2. [Node 02: Resource and Registry](nodes/02-resource-and-registry.zh-en.md)
3. [Node 03: Chat and Runtime](nodes/03-chat-and-runtime.zh-en.md)
4. [Node 04: Memory System](nodes/04-memory-system.zh-en.md)
5. [Node 05: Provider Layer](nodes/05-provider-layer.zh-en.md)
6. [Node 06: Database and Migrations](nodes/06-database-and-migrations.zh-en.md)

## Notes

- 配置统一通过工作区根目录 `.env` 管理，模板见 `.env.example`。
- 文档为中英双语混排，方便团队协作。
- 当前代码事实入口见 [Code and API Map](reference/code-api-map.zh-en.md)。
- Workbench 支持项目筛选、Agent 下拉选择、历史会话、Run Timeline 和事件查看。
- Memory retry 支持 API fallback 与 Celery + Redis enqueue 模式。
