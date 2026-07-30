# Skills Runtime Improvement Plan

**Language:** 中文为主，保留英文术语以便和代码、API、Anthropic Skill 规范对应。

---

<a id="中文"></a>

## 中文

### 1. 背景与目标

当前 HyperAgents 的 Agents、Tools、MCPs、Knowledge 已基本完成，Skills 也已经支持上传、解析、绑定和基础测试，但实际辅助效果仍明显弱于 opencode、Codex 等 Agent 工具中同一批 Skill 的表现。

目标不是继续堆更多提示词，而是把 Skills 从“提示词上下文”升级为“Agent 可发现、可激活、可执行、可验证、可产出文件”的 Runtime 能力。

最终目标：

| 能力 | 目标 |
|------|------|
| Discovery | Agent 启动或对话时只读取 Skill 名称、描述、capabilities |
| Activation | 用户任务匹配时加载完整 `SKILL.md` |
| Execution | 有脚本的 Skill 能被 Agent 当作工具调用 |
| Artifact | 需要生成文件的 Skill 能稳定保存到 My Files |
| Verification | xlsx/html 等产物能执行验证与修复 |
| Observability | 前端能看到 Skill 是否激活、脚本是否执行、产物保存路径和错误 |

---

### 2. 当前问题诊断

#### 2.1 Skill 还没有真正作为 Tool 接入 Agent

当前 ReAct Agent 的工具管理器中，`ToolManager._load_skill_tool()` 仍是 TODO。因此即使 Agent 绑定了 Skill，模型也不能像调用 MCP/tool 一样调用 Skill。

表现：

- `front-design` 看起来“激活”了，但本质上主要是 system prompt 注入。
- `xlsx` 虽然有 `scripts/recalc.py`，但 Agent 不能主动调用它，只能依赖后端固定分支。
- 模型不知道自己能写文件、跑脚本、读取附带资源，只会在聊天里输出内容。

#### 2.2 chat.py 中存在临时硬编码兜底

当前 `chat.py` 里有针对 `front-design`、`xlsx` 的专项逻辑，例如：

- 根据名称判断是否为 `front-design` 或 `xlsx`。
- 手写 `_build_front_design_fallback_html()`。
- 手写 `_build_generic_xlsx_artifact()`。
- 根据关键字生成表格或保存 HTML。

这些兜底能让测试“有结果”，但会让 Skill 的真实能力被后端固定逻辑盖住，导致用户意图复杂时效果差。

#### 2.3 front-design 缺少视觉闭环

`front-design` 是纯指导型 Skill。它的价值在于：

1. 基于主题形成独特视觉方向。
2. 批判通用模板感。
3. 编写页面。
4. 截图检查。
5. 迭代修正。

当前系统只有一次 LLM 输出 HTML，没有浏览器截图、首屏检查、空白检查、移动端检查、CSS 溢出检查，所以效果明显不如具备浏览器环境的 Agent 工具。

#### 2.4 xlsx 缺少生成-验证-修复闭环

`xlsx` Skill 的 `recalc.py` 是公式重算和错误检查脚本，不是通用生成器。正确工作流应该是：

1. 读取用户需求或现有文件。
2. 制定 workbook plan。
3. 使用 openpyxl/pandas 生成或修改。
4. 运行 `scripts/recalc.py`。
5. 如果发现公式错误，修复后再次 recalc。
6. 保存最终 workbook 到 My Files。

当前系统主要是后端通用生成一个 workbook，再跑一次 recalc，缺少对 `SKILL.md` 规则的完整执行。

---

### 3. 改造原则

1. **Skill 不等于提示词片段**  
   Skill 是一个能力包，必须有明确的发现、激活、执行、验证生命周期。

2. **Instruction Skill 和 Executable Skill 分开处理**  
   无脚本 Skill 走 instruction/artifact pipeline；有 `entrypoint` 的 Skill 作为工具执行。

3. **不要按具体测试词硬编码业务场景**  
   不要固定“销售表”“班级表”“卖花网站”“猫粮网站”等。后端只提供通用执行框架，业务内容由用户请求和 Skill 指令决定。

4. **文件型任务必须产出文件**  
   用户要求生成 HTML/XLSX 时，不应把大段代码贴在聊天里。应该保存到 My Files，并返回路径。

5. **验证优先于表面成功**  
   xlsx 需要公式验证；HTML 需要渲染检查；脚本执行需要 stdout/stderr 和 execution record。

---

### 4. 改造步骤

#### Phase 1：修通 SkillTool 执行链路

目标：让有 `entrypoint` 的 Skill 真正成为 Agent 可调用工具。

后端改造：

1. 实现 `ToolManager._load_skill_tool()`。
2. 对每个绑定 Skill：
   - 如果存在 `entrypoint`，创建 `SkillTool`。
   - tool name 使用安全名称，例如 `skill_xlsx`。
   - tool description 来自 `description`/`purpose`。
   - parameters 来自 `input_schema`，缺省时提供通用 `{ input_text, files }` schema。
3. `SkillTool.execute()` 调用 `SkillRuntime.execute()`。
4. `SkillRuntime.execute()` 保存 `generated_files` 到 My Files。
5. `RuntimeRunEvent` 记录：
   - skill name
   - input
   - status
   - stdout/stderr
   - saved_files
   - error_message

验收标准：

- Agent 绑定 xlsx 后，ReAct 工具列表能看到 xlsx skill tool。
- 用户要求生成或修改 spreadsheet 时，Agent 能触发 skill tool。
- 前端 runtime trace 能看到 `skill_runtime` 执行记录。

---

#### Phase 2：建立 Skill Activation Engine

目标：把 Skill 选择从散落在 `chat.py` 的正则判断变成统一组件。

新增模块建议：

```text
backend/app/runtime/skill_activation.py
```

核心函数：

```python
class SkillActivationResult(BaseModel):
    discovery_prompt: str
    activated_skills: list[dict]
    activation_reasons: list[dict]

class SkillActivationEngine:
    def discover(bound_skills) -> str: ...
    def activate(user_text, bound_skills) -> SkillActivationResult: ...
```

激活策略：

1. 用户明确说“使用 xlsx skill” → 强激活。
2. 用户任务与 Skill description/capabilities 高置信匹配 → 激活。
3. 询问“你有什么 skill” → 只返回绑定清单，不进入 LLM。
4. 仅绑定一个 Skill 不应无条件激活，除非匹配任务类型。

验收标准：

- 未绑定 Skill 时，询问 Skill 清单返回“当前没有绑定任何 Skill”。
- 绑定 MCP 但未绑定 Skill 时，不把 MCP 能力说成 Skill。
- 同时绑定多个 Skill 时，只激活相关 Skill。

---

#### Phase 3：Artifact Skill Pipeline

目标：文件型 Skill 不再依赖聊天回答，而是进入专门产物流水线。

建议新增：

```text
backend/app/runtime/artifact_skills/
  base.py
  html_design.py
  spreadsheet.py
```

##### 3.1 front-design Pipeline

流程：

1. 加载完整 `SKILL.md`。
2. 让模型生成设计计划，但计划不展示给用户。
3. 让模型生成完整单文件 HTML。
4. 保存到 My Files。
5. 使用 Playwright 或可用浏览器工具渲染截图。
6. 检查：
   - 页面非空
   - 首屏有主题信号
   - 文本无明显溢出
   - 桌面/移动端布局可用
   - 无外部依赖导致空白
7. 如检查失败，带截图/错误摘要让模型修复。
8. 最终返回文件路径。

建议输出：

```text
已使用 front-design Skill 生成网站首页文件。

文件已保存到 My Files：
- generated/front-design_YYYYMMDD_HHMMSS/homepage.html

验证：desktop/mobile 渲染通过。
```

##### 3.2 xlsx Pipeline

流程：

1. 根据用户请求生成 workbook plan JSON：
   - sheets
   - columns
   - sample rows
   - formulas
   - formatting
   - assumptions
2. 使用 openpyxl/pandas 创建或修改 workbook。
3. 如果包含公式，运行 `scripts/recalc.py`。
4. 若 `errors_found`，自动修复并再次 recalc。
5. 保存 workbook 到 My Files。
6. 可选生成 README sheet，说明假设、可编辑区域、公式说明。

验收标准：

- 用户要求“生成表格”时返回 `.xlsx` 文件路径，而不是 HTML 或聊天表格。
- 公式使用 Excel 公式，不硬编码结果。
- recalc 成功或明确记录 LibreOffice 不可用原因。

---

#### Phase 4：Skill 测试与观测 UI

目标：前端可以直接判断 Skill 是否真的执行。

Skills 详情页增加 Test 面板：

| 区域 | 内容 |
|------|------|
| Input | 用户输入、文件选择、JSON input_data |
| Activation | 是否激活、激活原因、加载了哪些指令 |
| Runtime | 是否执行脚本、耗时、stdout/stderr |
| Output | output_data、saved_files、错误 |
| Files | 生成文件下载入口 |

Workbench 增强：

- Assistant 消息下显示 `Skill: front-design`。
- Runtime Trace 中显示 skill discovery / activation / execution / artifact / verification。
- 如果 Skill 只是 instruction-only，要明确显示 `Instruction-only Skill, no script entrypoint`。

---

### 5. front-design 专项提升建议

短期可做：

1. 不再把 HTML 直接展示在聊天里。
2. 保存后返回 My Files 路径。
3. 增加 HTML 渲染检查，至少检查文件不为空、有 `<body>`、有可见文本。
4. Prompt 中强制模型先内部构思再输出完整 HTML。

中期可做：

1. 集成 Playwright 截图。
2. 失败时自动二次修复。
3. 生成 `preview.png` 一并保存。
4. 将设计质量检查结果写入 Runtime Trace。

长期可做：

1. 支持用户上传品牌素材。
2. 支持多方案生成和选择。
3. 支持设计记忆，避免每次都是相似风格。

---

### 6. xlsx 专项提升建议

短期可做：

1. 根据用户需求生成 workbook plan，而不是直接泛化表头。
2. 文件名、sheet 名、列名严格来自用户请求。
3. 运行 `recalc.py` 后把结果写入 trace。
4. 如果 LibreOffice 不可用，明确提示“公式已写入但未重算”。

中期可做：

1. 支持编辑用户上传的 xlsx 文件。
2. 对现有文件双 pass 读取：公式和值分开读。
3. 支持保留格式、冻结窗格、筛选、条件格式。
4. 自动生成公式检查报告。

长期可做：

1. 支持图表、透视表、数据验证下拉。
2. 支持多 sheet 财务模型。
3. 支持对比修改前后 workbook。

---

### 7. 建议优先级

| 优先级 | 工作项 | 价值 |
|--------|--------|------|
| P0 | 实现 `SkillTool` 和 `SkillRuntime` 工具调用 | 让 Skill 真正可执行 |
| P0 | Skill 清单/激活逻辑确定性化 | 避免幻觉和误激活 |
| P0 | 文件型任务保存到 My Files | 符合用户预期 |
| P1 | front-design HTML 渲染验证 | 显著提升页面质量 |
| P1 | xlsx plan → generate → recalc → repair | 显著提升表格质量 |
| P1 | Skill Test UI | 方便定位问题 |
| P2 | Docker/venv 隔离和依赖管理 | 提升安全性和兼容性 |
| P2 | Skill 市场/版本管理 | 生态能力 |

---

### 8. 与 Workflow 的关系

Workflow 会调用多个 Agent，而每个 Agent 又可能绑定 Tools、MCPs、Knowledge、Skills。因此建议先把 Skills Runtime 补强，再做 Workflow。否则 Workflow 可以跑起来，但复杂步骤中 Skill 仍会不稳定，最终影响整个流程质量。
---

### 9. 2026-07-29 实现补充：Generic Skill Code Runner

本轮已补充通用 `SkillCodeRunner`，用于处理 **instruction-only Skill** 的文件型任务。

相关文件：

```text
backend/app/runtime/skill_code_runner.py
backend/app/api/v1/chat.py
```

当前执行路径：

| Skill 类型 | 执行方式 |
|-----------|----------|
| 有 `entrypoint` | 通过 `SkillRuntime` 直接执行 Skill 包内声明的入口脚本 |
| 无 `entrypoint`，但任务需要生成/修改文件 | 通过 `SkillCodeRunner`：模型基于 `SKILL.md` 生成临时 Python 脚本，后端在临时 workspace 执行，收集 `outputs/`，保存到 My Files |
| 无 `entrypoint`，且不是文件型任务 | 作为普通 instruction Skill 注入 LLM，上下文中只加载被激活 Skill 的完整说明 |

`SkillCodeRunner` 的通用约束：

1. 不按 Skill 名称写死业务逻辑，例如不再内置 `xlsx.py`、不按“销售表/班级表/卖花网站”等测试词分支。
2. 输入文件只来自用户在 My Files 中引用的相对路径，例如 `uploads/.../file.xlsx`。
3. 执行时复制 Skill 包到临时 `SKILL_DIR`，复制输入文件到临时 `INPUTS_DIR`。
4. 生成脚本只能把最终产物写入 `OUTPUTS_DIR`。
5. 后端只收集 `OUTPUTS_DIR` 文件并保存到 My Files。
6. Runtime Trace 会记录 `skill_code_runner` 的 succeeded/failed、stdout/stderr 摘要、saved files。
7. 文件型任务不能只以“脚本退出码为 0”作为成功标准；Runner 需要做产物后验校验。当前已加入 spreadsheet blank-column 任务的格式级校验：如果源文件存在 header-only 空白列，而输出仍保留这些列，则自动尝试简单修复，修复后仍失败才返回失败。

对 xlsx 官方 Skill 的影响：

- `xlsx/scripts/recalc.py` 仍然是 Skill 自带辅助脚本，不是自动入口。
- 当用户要求创建、编辑、清理或另存 spreadsheet 文件时，`SkillCodeRunner` 会把完整 `SKILL.md`、输入文件列表、Skill 包文件列表交给模型，让模型生成临时 Python 执行脚本。
- 生成脚本可以按 `SKILL.md` 要求使用 `openpyxl`/`pandas`，必要时调用 `Path(SKILL_DIR) / "scripts" / "recalc.py"`。

验收方式：

1. 在 Workbench 中选择绑定了 xlsx Skill 的 Agent。
2. 上传或选择 My Files 中的 xlsx 文件。
3. 输入类似：

```text
使用xlsx skill 帮我把这个文件uploads/YYYYMMDD_xxxxxx/example.xlsx中的空白列删掉，另存为一个新的xlsx文件
```

4. 预期结果：
   - Assistant 返回 My Files 中的新 `.xlsx` 路径。
   - Runtime Trace 出现 `skill_code_runner` 事件。
   - 新文件与源文件不同，且只按用户请求做必要修改。

后续优化：

1. 对生成脚本增加更严格的 filesystem sandbox 和 import policy。
2. 对 xlsx 增加自动 recalc/公式错误二次修复结果摘要。
3. 对 HTML 类产物增加 Playwright 截图和非空/响应式检查。
4. 在 Skills 页面增加 Test 面板，展示 Discovery、Activation、Code Generation、Execution、Saved Files。
---

### 10. 2026-07-29 实现补充：load_skill Progressive Disclosure Tool

参考 `D:\work\LLM_development_learning\Agent_skills_demo\demo1\src\agent` 中的 demo，本轮补充了 `load_skill` 工具模式。

借鉴点：

1. 初始只展示 Skill catalog：`name + description + executable + scripts`。
2. 模型需要完整 Skill 指令时，通过 `load_skill(skill_name)` 加载完整 `SKILL.md`。
3. `load_skill` 返回完整指令和 Skill 包内 `scripts/*.py` 列表。
4. ReAct 模式和 legacy function-calling 模式都会记录 `skill loaded` Runtime Trace。

相关代码：

```text
backend/app/runtime/skill_loader.py
backend/app/runtime/agent_engine/tool_manager.py
backend/app/runtime/agent_engine/react_agent.py
backend/app/api/v1/chat.py
backend/app/runtime/skill_activation.py
```

当前实现是兼容式接入：

- 保留确定性 Skill Activation 和已跑通的 Skill Code Runner，避免破坏现有 xlsx/front-design 文件任务。
- 新增 `load_skill` 工具，让支持工具调用或 ReAct 的模型可以像 demo 一样按需加载完整 Skill 内容。
- ReAct 即使已有 agent/system prompt，也会追加工具使用说明，确保 `load_skill` 在 Action 列表中可见。

后续建议：

1. 将 `skills_loaded` 做成 session/run state，而不只是单次 tool observation。
2. 已加载 Skill 后再动态暴露该 Skill 关联的 MCP/tools/code-runner 能力，减少工具噪声。
3. 在 Workbench Runtime Trace 中单独展示 Skill catalog、load_skill、loaded skills、Skill Code Runner 四个阶段。
4. 逐步减少确定性 full SKILL.md 注入，过渡到真正的 catalog -> load_skill -> execute 模式。
## English Companion Summary

This design note explains how the Skill runtime should behave like a general Agent Skill system instead of hard-coding behavior for specific test Skills such as xlsx or front-design.

Key goals:

1. Preserve progressive disclosure: discover Skill names and descriptions first, load full `SKILL.md` only when relevant, and execute scripts only when the Skill package explicitly declares an executable entrypoint.
2. Avoid prompt-specific backend branches. The runtime must not hard-code examples such as sales tables, class score sheets, flower websites, or any other business prompt.
3. Support instruction-only Skills and executable Skills. Instruction-only Skills guide the Agent through `SKILL.md`; executable Skills run through a generic runtime contract.
4. Use a generic Skill Code Runner for uploaded scripts. Script execution should come from the Skill package itself, not from backend artifact-specific modules.
5. Save generated artifacts to My Files and return file paths instead of dumping large HTML/XLSX content into chat responses.
6. Keep the runtime extensible for future Skills with different scripts, templates, and workflows.

Implementation status note:

The current codebase includes Skill activation, SkillRuntime, Skill Code Runner, artifact persistence to My Files, and documentation updates. Treat this design file as the improvement plan; use `docs/modules/skills.zh-en.md` for the current runtime contract.
