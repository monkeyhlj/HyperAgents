# Node 04: Memory System (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## Memory 是平台级节点 / Memory as a platform-level node

Memory 不是聊天历史的别名，而是独立服务。当前支持 scope/type：

- `conversation`
- `project`
- `agent`
- `execution`
- `global`

## Memory APIs

- `POST /api/v1/memory`
- `GET /api/v1/memory`
- `POST /api/v1/memory/semantic-search`
- `POST /api/v1/memory/retry-embeddings`

## 自动向量化 / Automatic Embedding

`POST /api/v1/memory` 默认 `auto_embedding=true`，服务端自动调用 Embedding Provider。若只想写结构化 memory 而不生成向量，可传 `auto_embedding=false`。

## 向量维度 / Embedding Dimensions

- 默认 `MEMORY_EMBEDDING_DIMENSIONS=1536`。
- `memory_records.embedding` 使用 pgvector，并按配置维度建模。
- `semantic-search.query_embedding` 的维度必须和 `MEMORY_EMBEDDING_DIMENSIONS` 一致，否则返回明确错误。
- 如果更改维度，需要同步数据库迁移和历史数据策略。

## 降级与重试 / Fallback and Retry

- embedding 失败时，memory 记录仍会写入。
- `embedding_status=failed`。
- 记录 `embedding_error`。
- 可通过 `retry-embeddings` 重试。
- `enqueue=true` 且 Worker 可用时进入 Celery；否则回退到 API 进程执行。

## 混合检索 / Hybrid Retrieval

语义检索支持 `similarity_weight`：

`hybrid_score = similarity_weight * similarity_score + (1 - similarity_weight) * importance_score`

## 代码位置 / Code References

- `backend/app/api/v1/memory.py`
- `backend/app/services/memory_store.py`
- `backend/app/runtime/embeddings.py`
- `backend/app/schemas/memory.py`
- `backend/app/workers/tasks.py`
- `backend/app/db/models.py`
