# HyperAgents Docs (中文 + English)

导航 / Navigation: [返回项目首页](../README.md) | [中文 README](../README.zh.md) | [English README](../README.en.md)

本目录用于解释当前项目每个核心节点（Node）、如何测试、以及如何接入外部资源。
This folder explains each core node in the project, how to test it, and how to integrate external resources.

中文：当前后端数据库配置、模型 Provider 配置、前端 API 地址配置统一通过工作区根目录 `.env` 管理（模板：`.env.example`）。
English: Backend database settings, model provider settings, and frontend API endpoint are centrally managed via workspace-root `.env` (template: `.env.example`).

## 文档导航 / Navigation

1. `docs/quick-start.zh-en.md`
   - 项目快速上手与运行顺序
   - Quick start and recommended run order
2. `docs/nodes/01-project-and-members.zh-en.md`
   - Project 与成员权限节点
   - Project and membership node
3. `docs/nodes/02-resource-and-registry.zh-en.md`
   - Resource 与 MCP/Tool/Skill Registry 节点
   - Resource and MCP/Tool/Skill registry node
4. `docs/nodes/03-chat-and-runtime.zh-en.md`
   - Chat 会话与 Runtime 执行节点
   - Chat sessions and runtime execution node
5. `docs/nodes/04-memory-system.zh-en.md`
   - Memory 系统（分层、降级、重试、混合检索）
   - Memory system (layers, fallback, retry, hybrid retrieval)
6. `docs/nodes/05-provider-layer.zh-en.md`
   - LLM/Embedding Provider 统一适配层
   - Unified LLM/Embedding provider layer
7. `docs/nodes/06-database-and-migrations.zh-en.md`
   - PostgreSQL/pgvector + Alembic 节点
   - PostgreSQL/pgvector + Alembic node
8. `docs/testing-playbook.zh-en.md`
   - 手把手测试清单（API + 前端）
   - Step-by-step test checklist (API + frontend)
9. `docs/external-resources-integration.zh-en.md`
   - 应该添加哪些外部资源、为什么、怎么加
   - What external resources to add, why, and how

## 当前系统节点总览 / Current Node Map

- Project
- Member/Auth Header (`x-user-id`)
- Resource (agent/workflow/tool/skill/mcp/knowledge_base)
- Registry (mcp/tool/skill)
- Chat Session + Message
- Runtime Executor
- LLM Providers (OpenAI + localhost)
- Memory Service
- Embedding Providers (OpenAI + localhost)
- Memory Retry Job Queue (DB-based)
- Database Models (PostgreSQL + pgvector)
- Alembic Migrations
- Frontend Console (Dashboard/Projects/Resources/Workbench)

## 推荐阅读顺序 / Suggested Reading Order

1. `docs/quick-start.zh-en.md`
2. `docs/nodes/01-project-and-members.zh-en.md`
3. `docs/nodes/02-resource-and-registry.zh-en.md`
4. `docs/nodes/03-chat-and-runtime.zh-en.md`
5. `docs/nodes/04-memory-system.zh-en.md`
6. `docs/testing-playbook.zh-en.md`
7. `docs/external-resources-integration.zh-en.md`
