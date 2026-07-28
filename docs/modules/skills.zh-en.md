# Skills Module Guide / Skills 模块说明

状态 / Status: Resource model, progressive disclosure, and local Python SkillRuntime are implemented.

## Purpose / 作用

中文：
用于管理可复用技能定义，给 Agent 提供行为模板、操作说明或能力片段。当前 Skill 以资源形式保存，并可在 Agent 配置中关联。

English:
Manages reusable skill definitions that provide behavior templates, operating instructions, or capability snippets for agents. Skills are currently stored as resources and can be associated with Agents.

## Current Scope / 当前范围

1. Skill 资源创建、编辑、删除、查询。
2. Skill 与 Agent 的配置关联。
3. 通过 `config` 保存结构化技能元数据。
4. Agent 问答时按渐进式披露执行 Skill：先发现摘要，匹配任务后加载完整 `SKILL.md`。
5. 对声明了 Python `entrypoint` 的 Skill，后端可通过 SkillRuntime 执行脚本，并把产物保存到 My Files。

## Runtime Semantics / 运行时语义

Agent Skill 是一份“怎么做”的说明书，核心文件是 `SKILL.md`。系统按渐进式披露使用 Skill：

1. **Discovery / 发现**：Agent 只读取绑定 Skill 的名称、description/purpose 和少量能力摘要，用于判断是否相关。
2. **Activation / 激活**：用户请求显式点名 Skill，或任务与 Skill 描述匹配时，才把该 Skill 的完整 `SKILL.md` 正文加入 Agent 上下文。
3. **Execution / 执行**：Agent 按 `SKILL.md` 指令完成任务；如果 Skill 声明了可执行 Python `entrypoint` 且文件存在，则 SkillRuntime 会在隔离临时工作目录中调用该脚本。

当前 SkillRuntime 支持的执行契约：

- `entrypoint` 格式：`scripts/module:function`，例如 `scripts/main:execute`。
- 只执行上传 Skill 包内部的 entrypoint 文件；不会自动遍历或执行任意脚本。
- entrypoint 函数可接受以下签名之一：
  - `execute(input_data, context)`
  - `execute(input_data=input_data, context=context)`
  - `execute(input_data)`
  - `execute()`
- `input_data` 包含用户文本、project/session/agent/user id 和 Agent config。
- `context` 包含临时 `work_dir` 与 `outputs_dir`。脚本可把产物写入 `outputs/`，系统会自动收集并保存到 My Files。
- 脚本也可以返回 `{"generated_files": [{"filename": "...", "content": "..."}]}` 或 `content_base64`，系统会保存这些文件。
- 每次执行会写入 `skill_executions`，并在聊天 Runtime Timeline 中记录 `skill_runtime` 事件。

当前限制：

- 运行时是本地 Python subprocess，不会自动安装 requirements，也不会启用网络或 Docker 沙箱。
- 没有可执行 entrypoint 的 Skill 不会报错，会作为说明型 Skill 使用，并在 Runtime Timeline 中显示 skipped。
- 依赖外部程序的脚本需要运行环境已安装对应程序，例如 xlsx 的 LibreOffice/`soffice` 重算脚本需要系统 PATH 中存在 `soffice`。
- 如果缺少 `soffice`，xlsx 的 `scripts/recalc.py` 会执行失败并返回 `soffice not found on PATH`；这说明脚本被调用了，但运行环境缺少依赖。
- 没有声明 `entrypoint` 的 Skill 不会被虚构为 `scripts/main:execute`。这类 Skill 仍会按 `SKILL.md` 作为说明型 Skill 激活；附带脚本只有在运行时明确接入或由模型/代码执行环境按说明调用时才会运行。
- front-design 这类产物型说明 Skill 只有在模型返回完整 HTML 时才保存文件；后端不应再用固定 fallback 页面伪装成 Skill 生成结果。
- 对产物型 Skill，聊天回答优先返回 My Files 路径，而不是直接展示大段 HTML/XLSX 内容。
- Skill Runtime 不应把具体业务意图写死在后端代码里，例如某一种报表、某一个行业首页或某个测试提示词。用户意图始终来自当前请求，Skill 只提供可复用的工作流、规则、脚本和参考资料。
- 当 Skill 没有可执行 entrypoint，或模型输出需要保存为文件时，后端只能使用通用 artifact 管线：根据用户请求动态命名、抽取显式字段、保存文件；不能依赖“销售表”“班级表”“卖花网站”等固定关键词分支。

## Recommended Config Shape / 推荐配置结构

```json
{
  "category": "ops",
  "instructions": "Summarize alerts and propose next actions.",
  "inputs": ["alert_payload", "service_name"],
  "outputs": ["summary", "recommended_actions"],
  "tags": ["incident", "triage"]
}
```

## API Mapping / API 对照

- `POST /api/v1/resources/projects/{project_id}` with `kind=skill`: 创建 Skill。
- `GET /api/v1/resources/projects/{project_id}?kind=skill`: 查询项目 Skill。
- `PATCH /api/v1/resources/{resource_id}`: 更新 Skill。
- `DELETE /api/v1/resources/{resource_id}`: 删除 Skill。
- `POST /api/v1/registry/projects/{project_id}/skill`: 注册项目级 Skill。
- `GET /api/v1/registry/public/skill`: 浏览 public Skill。

## Test Checklist / 测试清单

1. 创建 Skill，并写入说明与结构化 `config`。
2. 在 Agent 中关联 Skill。
3. 保存 Agent 后重新打开，确认关联未丢失。
4. 验证 private/project/public 可见性。
5. 如需跨项目复用，将 Skill 设为 public 并通过 registry 浏览。

## Notes / 备注

- Skill 默认是说明型能力包；只有声明了有效 Python `entrypoint` 的 Skill 才会进入 SkillRuntime 脚本执行。
- 可执行 Skill 的文件产物应写入 `outputs/` 或返回 `generated_files`，系统会保存到 My Files。
- 复杂依赖、联网调用或强隔离需求仍建议优先使用 Tool、MCP 或后续 Docker Runtime。
