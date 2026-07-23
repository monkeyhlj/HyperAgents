# Node 06: Database and Migrations (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## 数据层 / Data Layer

当前使用 PostgreSQL + pgvector。核心表包括：

- `users`
- `projects`
- `project_members`
- `project_member_permissions`
- `resources`
- `chat_sessions`
- `chat_messages`
- `runtime_runs`
- `runtime_run_events`
- `memory_records`
- `memory_embedding_jobs`
- `provider_connections`

## 迁移层 / Migration Layer

使用 Alembic 管理 schema 版本，避免依赖 `create_all`。生产环境应保持 `AUTO_CREATE_TABLES=false`，统一通过迁移发布 schema。

## 迁移命令 / Migration Commands

迁移连接串通过 `DATABASE_URL` 从工作区根目录 `.env` 读取。

```powershell
cd backend
alembic upgrade head
```

新增迁移：

```powershell
cd backend
alembic revision --autogenerate -m "your change"
```

## 当前迁移 / Current Migrations

- `0001_initial_schema.py`: 初始项目、资源、聊天、memory、pgvector schema。
- `0002_memory_embedding_retry_and_status.py`: embedding retry/status 字段。
- `0003_add_users_and_auth.py`: users/auth。
- `0004_runtime_runs_and_events.py`: runtime runs/events。
- `0005_project_member_permissions.py`: member manager 权限。
- `0006_provider_connections.py`: 项目级 Provider Connection。

## 注意事项 / Notes

- 首次迁移会创建 `vector` extension。
- 如果数据库用户无权限创建 extension，需要 DBA 预先创建。
- `MEMORY_EMBEDDING_DIMENSIONS` 默认 1536；数据库向量维度和配置需要一致。
- Provider Connection 的 API Key 以加密文本保存，生产环境必须配置稳定的 `PROVIDER_CONNECTION_SECRET_KEY`。

## 代码位置 / Code References

- `backend/app/db/models.py`
- `backend/app/db/session.py`
- `backend/alembic/env.py`
- `backend/alembic/versions`
- `backend/app/core/config.py`
