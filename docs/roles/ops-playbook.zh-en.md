# Ops Playbook (中文 + English)

导航 / Navigation: [角色总览](roles-overview.zh-en.md) | [部署运维](../operations/deployment-operations.zh-en.md)

## 1) 目标 / Goal

中文：
保障服务稳定可用，确保发布流程可回滚、可监控、可追踪，并保护 Provider/MCP 等外部连接密钥。

English:
Keep services reliable and operable with rollback-ready deployment, monitoring, traceability, and protected Provider/MCP external credentials.

## 2) 部署优先级 / Deployment Priorities

1. PostgreSQL + pgvector 稳定性。
2. Alembic 迁移到 head。
3. FastAPI 服务健康检查与结构化日志。
4. `AUTH_SECRET_KEY` 与 `PROVIDER_CONNECTION_SECRET_KEY` 稳定管理。
5. Redis 与 Worker 可用性。
6. 前端静态资源发布一致性。

## 3) 发布流程 / Release Flow

1. 备份数据库。
2. 执行 Alembic 迁移。
3. 发布后端。
4. 发布 Worker。
5. 发布前端静态资源。
6. 验证 health、auth、provider connection、chat、runs/events。
7. 观察错误率、run failed 比率与队列堆积。

## 4) 回滚策略 / Rollback Strategy

1. 应用层回滚到上一个稳定版本。
2. 数据迁移若不可逆，优先做前向修复。
3. Provider 密钥加密 key 不随意变更；变更前需有重加密策略。
4. 保留发布前后关键指标快照用于比对。

## 5) 运维监控建议 / Monitoring Suggestions

1. API 5xx 比例。
2. 平均响应时间与 p95。
3. run failed 比率。
4. worker 任务失败与重试次数。
5. embedding 失败率。
6. Provider Connection 测试失败率。
7. MCP probe/call 超时率。
