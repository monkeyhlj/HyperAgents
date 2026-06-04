# Architecture Roadmap (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [前端指南](../guides/frontend-guide.zh-en.md)

## 1) 结论 / Conclusion

中文：
你收到的建议总体方向是正确的，而且和当前 HyperAgents 的方向高度一致。对你这个平台型产品，FastAPI + Vue3 前后端分离是更合适的。

English:
The recommendation is directionally correct and highly aligned with HyperAgents. For a platform product, FastAPI + Vue3 with frontend-backend separation is a better fit.

补充：
前端组件库继续使用 View UI Plus（iView 体系）即可，不需要切换到 Element Plus。

## 2) 现状对齐度 / Current Alignment

当前仓库已经具备：
- PostgreSQL + pgvector 基础（memory + embedding）
- Runtime 层雏形（chat provider dispatch）
- Registry 资源模型（tool/skill/mcp）
- 项目域与成员权限基础
- 前端 Workbench 与项目详情雏形

当前主要短板：
- Metadata / Runtime / Worker 仍在同一后端进程中，职责边界不清
- Runtime 仍以同步单次调用为主，缺少执行态（run/task）模型
- 异步任务仅有局部重试逻辑，缺少统一队列与任务观测
- 前端信息架构仍偏页面集合，尚未形成“项目中心 + 资源工作流”
- SDK / Sandbox / 插件生态尚未形成标准接口

## 3) Target Architecture (Keep FastAPI + Vue3 + View UI Plus)

### 3.1 Backend Logical Split

1. Metadata API
- 负责项目、用户、权限、资源定义、配置 CRUD。

2. Runtime API
- 负责 Agent/Workflow 运行入口、会话执行、工具调用编排。

3. Worker
- 负责异步任务、长任务、定时任务、重试、回调。

建议先逻辑拆分（同仓库、同部署），再物理拆分（独立服务）。

### 3.2 Frontend IA

前端建议从“页面并列”升级为“项目中心”结构：
- Project Home
- Resources (Agent/Workflow/Tool/Skill/MCP/KB)
- Workbench (chat/run/log)
- Memory
- Settings

继续使用 View UI Plus，不切换组件库。

## 4) Phased Plan

### Phase 1 (1-2 weeks): Domain Stabilization

后端：
- 把 API 从资源维度提升到项目上下文维度（project scoped endpoints first）
- 增加 run/session/message 的统一查询接口
- 固化 auth（token, refresh strategy, permission checks）

前端：
- 所有核心页面统一支持“项目过滤 + 项目上下文”
- Workbench 增加 agent 选择器、历史运行列表、运行详情抽屉
- 项目详情页补资源快捷创建

交付标准：
- 用户可在一个项目内完成：资源创建 -> 运行调试 -> 历史回放

### Phase 2 (2-4 weeks): Runtime Core

后端：
- 引入 runtime run model（run_id, status, timeline）
- Runtime 执行链统一：API -> Runtime -> Agent -> Tool/MCP -> Memory
- Tool/Skill 定义改为 code-first 元信息注册

前端：
- Workbench 增加 run timeline / step logs / token usage
- 资源页面支持版本与发布状态

交付标准：
- 单 Agent 与多步骤执行都能通过统一 Runtime 追踪。

### Phase 3 (2-3 weeks): Worker and Async

后端：
- 引入 Celery + Redis（或 Dramatiq + Redis）
- 把 embedding、报告生成、批量任务迁移到 worker
- 增加任务状态 API（pending/running/succeeded/failed）

前端：
- 增加任务中心页面（任务队列、重试、日志）

交付标准：
- 长任务不阻塞 API，请求与执行解耦。

### Phase 4 (4+ weeks): Platformization

- SDK（Python）用于 Tool/Skill/Agent 上传与自动注册
- MCP Registry 插件协议化（认证、探活、版本）
- Sandbox 执行环境（Docker 隔离）
- LangGraph 兼容层（code-first + low-code）

交付标准：
- 平台用户既可 UI 配置，也可代码开发并发布。

## 5) Repo Refactor Map (Incremental)

建议按“兼容迁移”方式调整，不做一次性大搬家：

1. backend/app/api/v1 下按 domain 分包（auth, projects, runtime, registry, memory）
2. backend/app/services 增加 runtime_service, run_service
3. backend/app/runtime 增加 orchestration 子目录（agent/workflow/tool/mcp）
4. backend/app/workers 新建任务入口（先放同仓库）
5. frontend/src/views 新增 ProjectDetail/Workbench 子模块目录
6. frontend/src/services/api.js 逐步按 domain 拆文件（authApi, projectApi, runtimeApi）

## 6) iView (View UI Plus) Strategy

- 保留 View UI Plus，不切 Element Plus
- 设计系统统一：Tag/Badge/Timeline/Table/Drawer/Modal 作为平台 UI 基础组件
- 优先做信息密度和可观测性，而非营销型视觉

## 7) Next Action (Recommended)

建议下一步直接实施：
1. Workbench Agent Selector + Run Timeline
2. Runtime Run Model（后端新增 run 表与查询接口）
3. Worker 基础接入（先 embedding job 外移）

完成这三项后，项目会从“可用 demo”进入“平台内核”阶段。
