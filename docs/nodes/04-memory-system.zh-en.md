# Node 04: Memory System (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## Memory 是平台级节点 / Memory as a platform-level node

中文：
Memory 不是聊天历史的别名，而是独立服务。当前支持 scope/type：
- conversation
- project
- agent
- execution
- global

English:
Memory is not just chat history. It is an independent service. Current scope/type values:
- conversation
- project
- agent
- execution
- global

## Memory APIs

- `POST /api/v1/memory`
- `GET /api/v1/memory`
- `POST /api/v1/memory/semantic-search`
- `POST /api/v1/memory/retry-embeddings`

## 自动向量化 / Automatic Embedding

中文：
`POST /api/v1/memory` 默认 `auto_embedding=true`，服务端自动调用 Embedding Provider。

English:
`POST /api/v1/memory` uses `auto_embedding=true` by default, so vectors are generated server-side.

## 降级策略 / Fallback Strategy

中文：
- embedding 失败时，memory 记录仍会写入
- `embedding_status=failed`
- 记录 `embedding_error`
- 自动入重试队列，可异步重试

English:
- If embedding generation fails, memory record is still saved
- `embedding_status=failed`
- `embedding_error` is stored
- Retry job is queued and can be retried asynchronously

## 混合检索 / Hybrid Retrieval

中文：
语义检索支持 `similarity_weight`：

`hybrid_score = similarity_weight * similarity_score + (1 - similarity_weight) * importance_score`

English:
Semantic retrieval supports `similarity_weight`:

`hybrid_score = similarity_weight * similarity_score + (1 - similarity_weight) * importance_score`

## 代码位置 / Code References

- `backend/app/api/v1/memory.py`
- `backend/app/services/memory_store.py`
- `backend/app/runtime/embeddings.py`
- `backend/app/schemas/memory.py`
- `backend/app/db/models.py`
