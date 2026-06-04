# HyperAgents Documentation

欢迎来到 HyperAgents 文档站。

Welcome to the HyperAgents documentation site.

这里提供从快速上手到架构节点、测试手册、外部接入与生产配置建议的完整路径。

This site provides a complete path from quick start to architecture nodes, testing playbooks, external integration, and production configuration guidance.

## Recommended Path

1. [Quick Start](guides/quick-start.zh-en.md)
2. [Role-based Reading Guide](roles/roles-overview.zh-en.md)
3. [Developer Playbook](roles/developer-playbook.zh-en.md)
4. [QA Playbook](roles/qa-playbook.zh-en.md)
5. [Ops Playbook](roles/ops-playbook.zh-en.md)
6. [PM Playbook](roles/pm-playbook.zh-en.md)
7. [Frontend Guide](guides/frontend-guide.zh-en.md)
8. [Runtime Run and Worker Guide](guides/runtime-run-worker.zh-en.md)
9. [API Changelog](reference/api-changelog.zh-en.md)
10. [Deployment and Operations Guide](operations/deployment-operations.zh-en.md)
11. [Testing Playbook](guides/testing-playbook.zh-en.md)
12. [Architecture Roadmap](reference/architecture-roadmap.zh-en.md)
13. [Node 01: Project and Members](nodes/01-project-and-members.zh-en.md)
14. [Node 02: Resource and Registry](nodes/02-resource-and-registry.zh-en.md)
15. [Node 03: Chat and Runtime](nodes/03-chat-and-runtime.zh-en.md)
16. [Node 04: Memory System](nodes/04-memory-system.zh-en.md)
17. [Node 05: Provider Layer](nodes/05-provider-layer.zh-en.md)
18. [Node 06: Database and Migrations](nodes/06-database-and-migrations.zh-en.md)
19. [External Resources Integration](guides/external-resources-integration.zh-en.md)

## Notes

- 配置统一通过工作区根目录 `.env` 管理，模板见 `.env.example`。
- 文档为中英双语混排，方便团队协作。
- Workbench 已支持项目筛选、Agent 下拉选择、Run Timeline 事件查看。
- Memory retry 已支持 enqueue 模式，可对接 Celery + Redis。
