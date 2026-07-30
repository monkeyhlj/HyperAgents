# Maintenance Audit / 维护与冗余审计

状态 / Status: Snapshot after the 2026-07-30 repository review.

## Purpose / 作用

这份文档记录“什么可以删、什么不能轻易删、以后如何判断”。它不是自动化扫描报告，而是结合路由、import、API、文档导航和运行入口做出的人工审计结论。

This document records what can be removed, what should be kept, and how future cleanup decisions should be made.

## Removed in This Audit / 本次已删除

| Path | Reason |
| --- | --- |
| `frontend/src/views/ResourcesView.vue` | 旧资源 Tabs 容器。当前路由直接使用 `ResourceOwnedListView.vue`，全项目无引用。 / Old Resources tabs container. Current routes use `ResourceOwnedListView.vue` directly, and no project-wide references remain. |
| `frontend/src/views/resources/SkillsListView.vue` | 旧 Skills 列表页。全项目无路由引用，并依赖不存在的 `stores/project` 与旧路由名 `resources-create`。 / Old Skills list page. It had no route references and depended on missing `stores/project` and the old `resources-create` route. |
| `frontend/src/services/api.js::listProjectSkills` | 只被旧 `SkillsListView.vue` 使用；当前 Skills 列表走统一 Resource API，Skill 详情走 `/api/v1/skills/{id}`。 / Used only by the old `SkillsListView.vue`; current Skill lists use the unified Resource API and Skill detail uses `/api/v1/skills/{id}`. |
| `backend/app/runtime/executor.py` | 旧 `RuntimeExecutor` 兼容包装器。当前 Chat、Resource preview、Workflow 都走 `llm_service`、`agent_runner` 或 `code_executor`，全项目无引用。 / Legacy `RuntimeExecutor` compatibility wrapper. Current Chat, Resource preview, and Workflow paths use `llm_service`, `agent_runner`, or `code_executor`; no project-wide references remain. |

## Keep Deliberately / 明确保留

| Path | Why keep it |
| --- | --- |
| `backend/app/runtime/artifact_skills/` | 空注册表是通用扩展点，用来避免把 xlsx/front-design 等具体 Skill 行为写死到后端。当前由 Chat API 引入。 |
| `backend/app/workers/celery_app.py` | Celery 命令入口，主要通过命令行引用：`celery -A app.workers.celery_app.celery_app worker -l info`。静态 import 扫描容易误判。 |
| `backend/alembic/versions/*` | 数据库迁移历史，即使旧迁移没有被源码 import 也不能删。 |
| `backend/data/**` | 运行期数据、上传 Skill 包、用户文件和生成产物。不要按“源码未引用”删除；应通过 My Files 或后台清理策略处理。 |
| `backend/app/api/v1/skills.py::list_project_skills` | 前端当前不用，但属于后端兼容 API。若要删除，应先更新 API changelog 并确认没有外部客户端依赖。 |
| `backend/app/runtime/workflow/template.py` and `routing.py` | 被 Workflow engine 使用，静态脚本可能因 import 形式误判。 |

## Cleanup Checklist / 清理判断清单

1. 先用 `rg -n "NameOrPath" frontend backend docs` 全项目查引用。 / First search project-wide references with `rg -n "NameOrPath" frontend backend docs`.
2. 前端页面必须同时检查 `frontend/src/router/index.js` 的动态 import。 / For frontend pages, also check dynamic imports in `frontend/src/router/index.js`.
3. 后端 API 文件必须检查 `backend/app/api/router.py` 的 include_router。 / For backend API files, check `include_router` calls in `backend/app/api/router.py`.
4. 命令入口、Celery 入口、Alembic 迁移、数据目录不能只按 import 判断。 / Command entry points, Celery entry points, Alembic migrations, and data directories must not be judged by imports alone.
5. 删除前跑构建或编译： / Before deleting, run build or compile checks:

```powershell
cd frontend
npm run build

cd ../backend
python -m py_compile app/main.py app/api/router.py app/api/v1/*.py app/runtime/*.py app/runtime/workflow/*.py app/services/*.py
```

6. 若删除 API 或数据库字段，必须同步更新： / If deleting APIs or database fields, update these together:
- `docs/reference/code-api-map.zh-en.md`
- `docs/reference/api-changelog.zh-en.md`
- 相关 `docs/modules/*.zh-en.md`
- 前端 `frontend/src/services/api.js`

## Documentation UX Suggestions / 文档体验建议

面向第一次访问 `monkeyhlj.github.io/HyperAgents/` 的用户，文档应按“先能跑、再理解、再开发、最后运维”的顺序组织： / For first-time visitors to `monkeyhlj.github.io/HyperAgents/`, docs should follow this order: get it running, understand it, develop it, then operate it.

1. 首页回答三个问题：这是什么、能做什么、我下一步点哪里。 / The homepage should answer three questions: what it is, what it can do, and where to go next.
2. Quick Start 不要承载所有细节，只保留本地跑通路径和第一条成功验证。 / Quick Start should not carry every detail; keep only the local happy path and first success check.
3. Module docs 面向使用者，少讲内部实现，多讲页面操作、输入输出和测试方式。 / Module docs are user-facing: focus on page operations, inputs/outputs, and testing rather than internals.
4. Node docs 面向开发者，讲代码位置、数据表、运行链路和扩展点。 / Node docs are developer-facing: explain code locations, tables, runtime chains, and extension points.
5. Design docs 放历史方案和未来计划，导航上单独分组，避免新用户误以为设计稿就是当前功能。 / Design docs contain historical plans and future proposals; keep them separately grouped so new users do not confuse proposals with current functionality.
6. Code and API Map 是当前代码事实页，任何接口、表、路由落地后都应更新。 / Code and API Map is the current code-facts page and should be updated whenever APIs, tables, or routes land.