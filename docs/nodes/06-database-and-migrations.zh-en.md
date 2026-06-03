# Node 06: Database and Migrations (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## 数据层 / Data Layer

中文：
当前使用 PostgreSQL + pgvector。核心表：
- projects
- project_members
- resources
- chat_sessions
- chat_messages
- memory_records
- memory_embedding_jobs

English:
Current stack is PostgreSQL + pgvector. Core tables:
- projects
- project_members
- resources
- chat_sessions
- chat_messages
- memory_records
- memory_embedding_jobs

## 迁移层 / Migration Layer

中文：
使用 Alembic 管理 schema 版本，避免只靠 `create_all`。

English:
Alembic manages schema versions, so we do not rely only on `create_all`.

## 迁移命令 / Migration Commands

中文：
迁移连接串通过 `DATABASE_URL` 从工作区根目录 `.env` 读取。

English:
Migration connection string is read from workspace-root `.env` via `DATABASE_URL`.

```powershell
cd backend
alembic upgrade head
```

新增迁移 / Create new migration:

```powershell
cd backend
alembic revision --autogenerate -m "your change"
```

## 注意事项 / Notes

中文：
- 首次迁移会创建 `vector` extension。
- 如果数据库用户无权限创建 extension，需要 DBA 预先创建。

English:
- Initial migration creates `vector` extension.
- If DB user cannot create extensions, ask DBA to pre-create it.

## 代码位置 / Code References

- `backend/app/db/models.py`
- `backend/alembic/env.py`
- `backend/alembic/versions/0001_initial_schema.py`
- `backend/alembic/versions/0002_memory_embedding_retry_and_status.py`
