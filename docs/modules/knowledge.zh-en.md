# Knowledge Module Guide / Knowledge 模块说明

状态 / Status: Knowledge Base resource implemented; memory search APIs are implemented separately.

## Purpose / 作用

中文：
用于管理知识库资源与知识检索相关配置。当前 Knowledge Base 是资源类型之一，可与 Agent 关联；实际记忆写入、关键字检索、语义检索由 Memory API 提供。

English:
Manages knowledge base resources and retrieval-related configuration. Knowledge Base is a resource kind that can be associated with Agents; memory write, keyword search, and semantic search are provided by the Memory API.

## Current Scope / 当前范围

1. Knowledge Base 资源创建、编辑、删除、查询。
2. Knowledge Base 与 Agent 的配置关联。
3. Memory 记录写入、普通查询、语义查询与 embedding retry。

## Recommended Config Shape / 推荐配置结构

```json
{
  "source_type": "docs",
  "source_uri": "s3://bucket/path or local/import/id",
  "chunking": {
    "strategy": "section",
    "max_tokens": 800
  },
  "retrieval": {
    "top_k": 5,
    "scope": "project"
  }
}
```

## API Mapping / API 对照

Knowledge Base resource:

- `POST /api/v1/resources/projects/{project_id}` with `kind=knowledge_base`
- `GET /api/v1/resources/projects/{project_id}?kind=knowledge_base`
- `PATCH /api/v1/resources/{resource_id}`
- `DELETE /api/v1/resources/{resource_id}`

Memory data:

- `POST /api/v1/memory`: 写入 memory record。
- `GET /api/v1/memory`: 普通查询。
- `POST /api/v1/memory/semantic-search`: 语义检索。
- `POST /api/v1/memory/retry-embeddings`: 重试失败或待处理 embedding。

## Test Checklist / 测试清单

1. 创建 Knowledge Base 资源并保存检索配置。
2. 在 Agent 中关联 Knowledge Base。
3. 写入 project/agent/conversation scope 的 Memory。
4. 执行关键字查询和 semantic-search。
5. 构造 embedding failed/pending 记录并验证 retry-embeddings。

## Notes / 备注

- Knowledge Base 资源描述“知识源和检索策略”；Memory API 管理实际记忆记录。
- 若使用语义检索，需要 PostgreSQL pgvector 和可用 embedding provider。
- Worker 非必需；开启后可用 Celery + Redis 排队执行 embedding retry。
