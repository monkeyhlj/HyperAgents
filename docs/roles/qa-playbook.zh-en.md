# QA Playbook (中文 + English)

导航 / Navigation: [角色总览](roles-overview.zh-en.md) | [测试手册](../guides/testing-playbook.zh-en.md)

## 1) 目标 / Goal

中文：
确保核心链路稳定：认证、项目权限、资源管理、Workbench 运行、Run Timeline、Memory 重试。

English:
Ensure stability for core flows: auth, project permissions, resource management, Workbench execution, run timeline, and memory retry.

## 2) 回归主路径 / Core Regression Path

1. 注册或登录。
2. 创建项目。
3. 创建 agent 资源。
4. 创建会话并发送消息。
5. 校验 runs/events 展示与状态一致。
6. 执行 memory retry（enqueue=false 与 enqueue=true）。

## 3) 高风险点 / High-risk Areas

1. 权限边界：跨项目访问应返回 403。
2. 认证边界：token 过期或缺失应返回 401。
3. 迁移一致性：缺迁移时应有明确错误可定位。
4. 队列回退：worker 不可用时不应导致 API 崩溃。

## 4) 验收输出 / Test Deliverables

1. 功能用例结果。
2. 回归影响面说明。
3. 阻断问题与复现步骤。
4. 发布建议（可发布/有条件发布/阻断发布）。
