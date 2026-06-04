# Developer Playbook (中文 + English)

导航 / Navigation: [角色总览](roles-overview.zh-en.md) | [文档首页](../README.md)

## 1) 目标 / Goal

中文：
快速搭建本地开发环境，完成一次从项目创建到 Workbench 运行的端到端闭环，并能定位常见故障。

English:
Set up local development quickly, complete one end-to-end flow from project creation to Workbench run, and troubleshoot common issues.

## 2) 最短路径 / Fast Path

1. [quick-start.zh-en.md](../guides/quick-start.zh-en.md)
2. [api-changelog.zh-en.md](../reference/api-changelog.zh-en.md)
3. [runtime-run-worker.zh-en.md](../guides/runtime-run-worker.zh-en.md)
4. [frontend-guide.zh-en.md](../guides/frontend-guide.zh-en.md)

## 3) 日常开发清单 / Daily Dev Checklist

1. 拉取代码后执行 Alembic 迁移到 head。
2. 启动 backend、frontend。
3. 使用登录接口获取 token，验证项目 API。
4. 在 Workbench 完成一轮 run，检查 runs/events。
5. 若涉及 embedding 重试，验证 enqueue 与 fallback 两种模式。

## 4) 关键代码区域 / Key Areas

1. Backend API: `app/api/v1`
2. Runtime: `app/runtime`
3. Worker: `app/workers`
4. Data models: `app/db/models.py`
5. Frontend workbench: `frontend/src/views/WorkbenchView.vue`

## 5) 提交前检查 / Pre-commit Checks

1. 后端测试通过。
2. 前端构建通过。
3. 新增 API 有文档更新。
4. 迁移脚本与模型变更一致。
