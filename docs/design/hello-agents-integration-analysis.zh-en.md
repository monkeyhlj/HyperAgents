# Hello-Agents / HelloAgents Integration Analysis for HyperAgents

本文档分析 Datawhale `hello-agents` 教程项目与 `jjyaoao/HelloAgents` 框架对 HyperAgents 的参考价值，并结合 HyperAgents 当前代码结构，评估是否可以替换当前基于 `LangChainLLMWrapper + 自研 ReActAgent + ToolManager` 的 agent engine。

This document analyzes Datawhale `hello-agents` and the `jjyaoao/HelloAgents` framework in the context of HyperAgents. It evaluates whether HyperAgents should replace, adapt, or selectively learn from HelloAgents.

> 结论先行 / Executive summary:  
> 不建议直接整体替换。建议采用“并行适配器 + 渐进迁移”的方式，引入 `hello_agents` 作为可选 engine，同时优先借鉴其 ToolResponse、TraceLogger、Context Engineering、Session/Memory、Task/Todo/DevLog 等机制，反哺 HyperAgents 当前 Skills 和 Workflow 的短板。

## 1. 调研对象 / Research Scope

本次调研涉及两个相关但不同的对象：

1. `datawhalechina/hello-agents`  
   一个系统性的 Agent 教程项目，覆盖 Agent 基础、Tool、Memory、MCP、RAG、Workflow、Multi-Agent、Agent 框架设计等内容。该项目的定位更偏教学和体系化学习。

2. `jjyaoao/HelloAgents` / PyPI `hello-agents`  
   一个可安装的 Agent 框架。README 描述其为“生产级多智能体框架”，包含 ReActAgent、PlanSolveAgent、ReflectionAgent、ToolRegistry、ToolResponse、ContextBuilder、TraceLogger、SessionStore、Skills、TodoWrite、DevLog 等能力。

参考资料 / References:

- Datawhale hello-agents: <https://github.com/datawhalechina/hello-agents>
- Datawhale README raw: <https://raw.githubusercontent.com/datawhalechina/hello-agents/main/README.md>
- HelloAgents framework: <https://github.com/jjyaoao/HelloAgents>
- HelloAgents package/readme: <https://github.com/jjyaoao/helloagents>

## 2. HyperAgents 当前处境 / Current HyperAgents Situation

HyperAgents 当前已经不是单纯的 LangChain 项目。虽然有一个文件叫 `llm_wrapper.py`，但从代码结构看，LangChain 只承担很薄的一层接口适配。

关键文件：

- `backend/app/runtime/agent_engine/llm_wrapper.py`
- `backend/app/runtime/agent_engine/react_agent.py`
- `backend/app/runtime/agent_engine/tool_manager.py`
- `backend/app/api/v1/chat.py`
- `backend/app/runtime/agent_runner.py`

### 2.1 当前 Agent 调用链

当前 ReAct engine 的调用链大致是：

```text
Chat API / Workflow Agent Runner
        ↓
读取 Project / Agent Resource / Provider Profile / Provider Connection
        ↓
LLMService + LLMRequest
        ↓
LangChainLLMWrapper
        ↓
ReActAgent.run(...)
        ↓
ToolManager.load_tools(agent_config, context)
        ↓
MCPTool / BuiltinTool / SkillTool / load_skill / KBTool
        ↓
AgentEvent: thought / action / observation / final_answer
        ↓
RuntimeRunEvent / ChatMessage / Workflow StepExecution
```

这里真正重要的是：

- `LLMService` 是 HyperAgents 自己的 provider abstraction。
- `LangChainLLMWrapper` 只是把 `LLMService.generate()` 包装成 LangChain LLM 接口。
- `ReActAgent` 是 HyperAgents 自己写的，不是 LangChain AgentExecutor。
- `ToolManager` 是 HyperAgents 自己写的，深度接入 MCP、Skill、Knowledge、My Files 输出上下文。

因此，问题不应表述为“能否把 LangChain Agent 替换为 HelloAgents Agent”。更准确的表述是：

> 能否把 HyperAgents 当前自研 ReAct Agent Engine，替换或并行为 HelloAgents Agent Engine？

### 2.2 当前痛点

从近期调试过程看，HyperAgents 当前痛点主要集中在：

1. Skills 效果不稳定  
   同一个 `front-design` 或 `xlsx` Skill，在其他 Agent 工具中效果更好，而在 HyperAgents 中输出质量偏弱。

2. Skill Runtime 泛化能力不足  
   之前已经多次强调不能对“销售表”“班级表”“卖花网站”等提示词硬编码。Skill 应该由自身 `SKILL.md` 和附带 scripts 决定能力。

3. Tool / Skill 结果协议不统一  
   当前工具结果常常只是字符串或 JSON 字符串，缺少统一的成功/失败、artifact、metadata、trace 格式。

4. ReAct 文本解析脆弱  
   当前 ReAct Agent 使用 `Thought / Action / Input / Final Answer` 文本格式解析。对不稳定模型，尤其是非严格遵循格式的 OpenAI-compatible 模型，容易失败。

5. Workflow 可观测性仍需加强  
   Workflow 已有 run history 和 step execution，但复杂分支、变量映射、失败恢复、调试体验还需要改进。

6. Context Engineering 还不够系统  
   Skills、Knowledge、历史对话、文件引用、Workflow 输入输出都在争夺上下文窗口，需要更明确的上下文构建策略。

## 3. HelloAgents 能提供什么 / What HelloAgents Offers

HelloAgents 值得重点关注的不是“替换 LangChain”这件事，而是它对一个 Agent 框架所需模块的完整拆分。

### 3.1 Agent 类型

HelloAgents 提供或强调的 Agent 类型包括：

- SimpleAgent
- ReActAgent
- ReflectionAgent
- PlanSolveAgent
- Multi-Agent / Sub-agent 模式

对 HyperAgents 的启发：

- 当前 HyperAgents 只有 legacy/function-calling 路径和自研 ReAct 路径。
- Workflow 已经开始承担多 Agent 编排，但单个 Agent 内部还缺少 Plan、Reflect、Task decomposition 等模式。
- 未来可以将 `engine_type` 扩展为：

```text
legacy
react
hello_react
hello_plan_solve
hello_reflection
```

但不建议一开始就全部接入，应先验证 `hello_react`。

### 3.2 ToolRegistry

HelloAgents 的 ToolRegistry 思路比当前 HyperAgents ToolManager 更框架化。它通常包含：

- tool 注册
- tool schema
- tool execution
- tool response
- tool tracing

HyperAgents 当前 `ToolManager` 已经能加载：

- MCP tools
- built-in tools
- load_skill tool
- executable skill tools
- KB tool placeholder

但缺点是：

- Tool 输出格式不够统一。
- Tool 调用可观测性不够集中。
- Tool 错误恢复策略较弱。
- Skill tool 与普通 tool 的边界不够清晰。

### 3.3 ToolResponse

这是最值得 HyperAgents 直接借鉴的点之一。

当前 HyperAgents 里 tool 结果可能是：

```text
字符串
JSON 字符串
dict
文件路径描述
异常文本
```

建议引入统一协议：

```json
{
  "ok": true,
  "content": "human readable result",
  "data": {},
  "artifacts": [
    {
      "path": "generated/xlsx_.../report.xlsx",
      "kind": "xlsx",
      "label": "Generated Excel file"
    }
  ],
  "metadata": {
    "tool": "skill_xlsx",
    "duration_ms": 1200
  },
  "error": null
}
```

好处：

- Chat answer 可以更稳定地提取文件输出。
- My Files 可以更清晰地展示生成来源。
- RuntimeRunEvent 可以存统一 payload。
- Workflow step output 可以结构化传递。
- 前端可以按 `artifacts` 自动渲染下载入口。

这比直接替换 Agent 更有价值。

### 3.4 TraceLogger / Observability

HelloAgents 强调可观测性。HyperAgents 已有：

- `runtime_runs`
- `runtime_run_events`
- workflow run history
- workflow step executions
- HTTP request logging

但缺少一套贯穿 Agent / Tool / Skill / Workflow 的统一 trace 语义。

建议借鉴 HelloAgents 思路，定义统一事件层：

```text
agent.start
agent.thought
agent.action
tool.start
tool.end
tool.error
skill.discovery
skill.load
skill.execute
skill.artifact
knowledge.retrieve
workflow.step.start
workflow.step.end
workflow.route.evaluate
agent.final
```

这样可以同时服务：

- Workbench 运行轨迹
- Workflow Detail run history
- Skill 调试
- 后端日志
- 后续性能分析

### 3.5 Context Engineering

HelloAgents 的 ContextBuilder / TokenCounter 对 HyperAgents 非常关键。

HyperAgents 当前上下文来源很多：

- system_prompt
- project prompt
- agent config
- user input
- chat history
- bound skill catalog
- activated skill full instructions
- knowledge retrieval chunks
- file references
- workflow input
- previous workflow step output
- tool observations

如果没有统一 ContextBuilder，最终容易出现：

- Skill 没有被完整加载
- Knowledge 抢占 Skill 上下文
- 历史消息太长
- Workflow step 输入输出混乱
- 模型忽略关键指令

建议 HyperAgents 引入自己的 `ContextBuilder`，不一定直接用 HelloAgents 实现，但可以借鉴分层结构：

```text
ContextBundle
  - system_layer
  - project_layer
  - agent_layer
  - skill_discovery_layer
  - skill_instruction_layer
  - knowledge_layer
  - file_layer
  - workflow_layer
  - conversation_layer
  - tool_observation_layer
```

并为每层设置 token budget 和优先级。

### 3.6 Session / Memory

HelloAgents 的 SessionStore / Memory 思路也值得参考。

HyperAgents 已有：

- chat_sessions
- chat_messages
- memory records
- knowledge base documents

但 Agent Engine 层并没有形成清晰的 session abstraction。当前大部分 session 逻辑散在 API 和 store 里。

建议：

- 后端 DB 仍使用 HyperAgents 现有 schema。
- Agent Engine 内部可以有 lightweight `AgentSessionContext`。
- 不直接替换 DB，不引入 HelloAgents session store 作为主存储。

## 4. 替换/适配方案总览 / Integration Options

下面从保守到激进列出多种方案。

## 5. 方案 A：保持现状，仅学习设计思想

### 5.1 做法

不引入 HelloAgents 依赖，不改 agent engine。只阅读其框架设计，并将思想吸收到 HyperAgents 自研实现中。

可吸收内容：

- ToolResponse 协议
- TraceLogger 事件语义
- ContextBuilder 分层上下文
- TodoWrite / DevLog 长任务辅助工具
- Plan-and-Solve / Reflection 的 prompt pattern

### 5.2 优点

- 风险最低。
- 不增加第三方依赖。
- 不影响当前 Chat、Workbench、Workflow。
- 可以优先解决当前 Skills 调试问题。

### 5.3 缺点

- 不能快速获得 HelloAgents 的完整框架能力。
- 仍需要自己实现很多机制。
- 短期 Agent 能力提升有限。

### 5.4 适合场景

如果当前目标是稳定已有功能、提升 Skills 输出质量，方案 A 是最稳的第一步。

## 6. 方案 B：只替换 LangChainLLMWrapper

### 6.1 做法

用 HelloAgents 的 LLM abstraction 替换或绕过 `LangChainLLMWrapper`。

### 6.2 判断

不推荐。

原因是 HyperAgents 当前并没有深度依赖 LangChain AgentExecutor。`LangChainLLMWrapper` 只是薄适配层，把 `LLMService` 包装给 ReActAgent 用。如果替换这一层，收益很小。

### 6.3 风险

- 可能破坏现有 provider_profile / provider_connection。
- HelloAgents 默认 LLM 配置体系未必适配 HyperAgents 项目级 Provider Connection。
- 替换后不一定改善 Skills 和 Workflow。

### 6.4 结论

这个方案看起来像“替换 LangChain”，但实际上没有抓住问题核心。不建议做。

## 7. 方案 C：新增 HelloAgents Adapter，并行 engine_type

### 7.1 做法

新增一个适配层，而不是替换现有实现。

建议新增：

```text
backend/app/runtime/agent_engine/hello_agents_adapter.py
```

或目录：

```text
backend/app/runtime/agent_engine/hello_agents/
  __init__.py
  llm_adapter.py
  tool_adapter.py
  event_adapter.py
  runner.py
```

新增 engine type：

```text
engine_type = "hello_react"
```

调用方式：

```text
chat.py / agent_runner.py
  if engine_type == "hello_react":
      run HelloAgents adapter
  elif engine_type == "react":
      run current ReActAgent
  else:
      run legacy
```

### 7.2 适配层职责

#### 7.2.1 LLM Adapter

将 HyperAgents `LLMService` 包装成 HelloAgents 可用 LLM。

输入仍来自：

- model_provider
- model_name
- provider_profile
- provider_connection_id
- provider_connection

不要让 HelloAgents 直接读取 `.env`，避免绕过 HyperAgents 的 Provider Connection 体系。

#### 7.2.2 Tool Adapter

将 HyperAgents ToolManager 加载出来的 tools 转成 HelloAgents ToolRegistry 可注册工具。

要适配：

- MCP tools
- built-in tools
- load_skill tool
- executable skill tools
- knowledge_base_search

#### 7.2.3 Event Adapter

将 HelloAgents trace 转成 HyperAgents `AgentEvent`：

```json
{
  "stage": "thought",
  "iteration": 0,
  "content": "...",
  "tool_name": null,
  "tool_input": null,
  "tool_result": null,
  "error": null,
  "metadata": {}
}
```

这样现有 RuntimeRunEvent、Workbench、Workflow history 不需要大改。

#### 7.2.4 Artifact Adapter

HelloAgents tool 输出如果包含文件，需要映射到 HyperAgents My Files：

```text
generated/<skill>_<timestamp>/<file>
```

并通过现有 file service / runtime context 保存。

### 7.3 优点

- 风险可控。
- 可以 A/B 测试当前 ReAct 和 HelloAgents ReAct。
- 不破坏现有 Skills / Workflow。
- 后续可以逐步迁移。

### 7.4 缺点

- 需要写适配层。
- 会暂时存在两套 Agent loop。
- 需要维护事件和工具协议映射。

### 7.5 适合场景

最推荐。尤其适合现在这个阶段：

- Resources 基本完成。
- Skills 和 Workflow 还在打磨。
- 需要验证新 Agent 框架能否改善质量。
- 不能破坏已有前端和后端运行链路。

## 8. 方案 D：只引入 HelloAgents 的 ToolResponse / Trace 思想

### 8.1 做法

不引入完整 HelloAgents Agent，只在 HyperAgents 自己的 ToolManager 和 SkillRuntime 中引入统一协议。

新增内部 schema：

```python
class ToolExecutionResult(BaseModel):
    ok: bool
    content: str = ""
    data: dict = {}
    artifacts: list[dict] = []
    metadata: dict = {}
    error: str | None = None
```

### 8.2 改造范围

- `Tool.execute()` 返回统一结果。
- `SkillTool.execute()` 返回统一结果。
- Skill Code Runner 返回 artifacts。
- MCPTool 返回 content + raw metadata。
- KBTool 返回 chunks + sources。
- ReActAgent observation 使用 `content`，RuntimeRunEvent payload 保存全量。

### 8.3 优点

- 直接解决当前 Skills 输出混乱问题。
- 不引入外部框架风险。
- 对 Workflow step output 也有帮助。

### 8.4 缺点

- 不能获得 HelloAgents 的 Plan/Reflection 等 Agent 能力。
- 需要重构部分 ToolManager 和 SkillRuntime。

### 8.5 推荐程度

非常推荐，而且可以和方案 C 并行。

## 9. 方案 E：完整迁移到 HelloAgents

### 9.1 做法

废弃当前 `LangChainLLMWrapper / ReActAgent / ToolManager`，全面使用 HelloAgents 的：

- LLM
- Agent
- ToolRegistry
- ToolResponse
- SessionStore
- ContextBuilder
- TraceLogger
- Skills

### 9.2 优点

- 架构可能更统一。
- 可以快速获得更多 Agent 类型。
- 减少自研 Agent loop 维护成本。

### 9.3 风险

风险非常高：

1. Provider Connection 体系需要重接。
2. Project-first Resource 模型需要重接。
3. Skill 上传、Skill Metadata、Agent Skill Binding 需要重接。
4. My Files 输出路径需要重接。
5. Workflow StepExecution 和 RunHistory 需要重接。
6. RuntimeRunEvent 事件格式需要重接。
7. 前端 Workbench 和 Workflow Detail 可能需要改。
8. HelloAgents 框架版本演进可能带来兼容风险。

### 9.4 结论

不建议当前阶段完整迁移。只有当方案 C 验证明显优于当前 engine，且 HelloAgents 的版本稳定、接口清晰后，才考虑逐步迁移。

## 10. 方案 F：以 Workflow 为边界接入 HelloAgents

### 10.1 做法

不改 Workbench Agent Chat，只在 Workflow 某些节点中支持 HelloAgents Agent。

例如 Workflow step 增加：

```json
{
  "id": "planner",
  "type": "hello_agents",
  "agent_mode": "plan_solve",
  "agent_id": "..."
}
```

### 10.2 优点

- 不影响普通 Agent Chat。
- 可以在 Workflow 中测试 PlanSolve/Reflection。
- 更适合复杂任务。

### 10.3 缺点

- Workflow 当前也在建设中，再引入新 engine 会增加复杂度。
- 调试路径更长。
- 如果基础 Tool/Skill 协议没统一，Workflow 中问题会更难查。

### 10.4 结论

可以作为第二阶段，不建议第一阶段做。

## 11. 方案 G：借鉴 HelloAgents，但坚持 HyperAgents 自研 Agent Engine

### 11.1 做法

保留 HyperAgents 自研 engine，但系统化重构：

- `AgentEngine` interface
- `LLMAdapter`
- `ToolRegistry`
- `ToolExecutionResult`
- `TraceEvent`
- `ContextBuilder`
- `ArtifactManager`

这相当于吸收 HelloAgents 设计，构建 HyperAgents 原生 Agent Engine。

### 11.2 优点

- 和 Project-first、Resource-first 完全一致。
- 长期可控。
- 不被第三方框架接口限制。

### 11.3 缺点

- 开发成本较高。
- 短期无法快速验证 HelloAgents 效果。

### 11.4 结论

长期推荐。短期可以与方案 C 配合：先 adapter 验证，再决定是否自研吸收。

## 12. 各方案对比 / Option Comparison

| 方案 | 风险 | 收益 | 工作量 | 是否推荐 | 说明 |
|---|---:|---:|---:|---|---|
| A 只学习思想 | 低 | 中 | 低 | 推荐 | 稳定推进，不破坏现有功能 |
| B 替换 LLM Wrapper | 中 | 低 | 中 | 不推荐 | 没抓住核心问题 |
| C HelloAgents Adapter | 中 | 高 | 中高 | 强烈推荐 | 可并行 A/B 测试 |
| D 引入 ToolResponse/Trace | 低中 | 高 | 中 | 强烈推荐 | 直接改善 Skills/Workflow 可观测性 |
| E 完整迁移 | 高 | 高但不确定 | 高 | 暂不推荐 | 会冲击整个系统 |
| F Workflow 层接入 | 中高 | 中高 | 中高 | 第二阶段 | 适合后续 Plan/Reflection 节点 |
| G 自研吸收 | 中 | 高 | 高 | 长期推荐 | 保持 HyperAgents 架构主权 |

## 13. 推荐路线 / Recommended Roadmap

综合当前 HyperAgents 的状态，推荐路线是：

```text
阶段 0：继续稳定当前功能
阶段 1：引入 ToolExecutionResult + TraceEvent
阶段 2：新增 HelloAgents Adapter，作为 hello_react engine
阶段 3：用 front-design / xlsx / MCP / Knowledge 做 A/B 对比
阶段 4：将有效能力吸收到 HyperAgents 原生 engine
阶段 5：考虑 Workflow 中引入 PlanSolve / Reflection 节点
```

## 14. 阶段 1：统一 Tool/Skill/Artifact 协议

这是最该先做的部分。

### 14.1 新增内部协议

建议新增：

```text
backend/app/runtime/agent_engine/result.py
```

定义：

```python
class ToolExecutionResult(BaseModel):
    ok: bool
    content: str = ""
    data: dict = Field(default_factory=dict)
    artifacts: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    error: str | None = None
```

### 14.2 修改 ToolManager

所有 tool 执行都返回统一结构：

- MCPTool
- BuiltinTool
- SkillTool
- KBTool
- load_skill

### 14.3 修改 ReActAgent

- Observation 给模型看 `result.content`。
- RuntimeRunEvent 保存完整 result。
- 如果 result.artifacts 有文件，自动进入 saved_file_paths。

### 14.4 对 Skills 的价值

这能解决当前 Skills 最大的问题之一：

- 模型到底执行了 Skill 没有？
- Skill 返回的是文件还是文本？
- 文件保存在哪里？
- 脚本有没有报错？
- 哪一步报错？

## 15. 阶段 2：HelloAgents Adapter 设计

### 15.1 文件结构

建议：

```text
backend/app/runtime/agent_engine/hello_agents_adapter/
  __init__.py
  llm_adapter.py
  tool_adapter.py
  event_adapter.py
  runner.py
```

### 15.2 LLM Adapter

目标：HelloAgents 不直接管理 provider，仍通过 HyperAgents `LLMService`。

伪代码：

```python
class HyperAgentsHelloLLM:
    def __init__(self, llm_service, provider, model_name, provider_profile, provider_connection):
        ...

    def chat(self, messages, tools=None, **kwargs):
        return llm_service.generate(LLMRequest(...))
```

重点：

- 保留 provider_profile。
- 保留 provider_connection_id。
- 保留 provider_connection。
- 支持 messages。
- 支持 tools 或 function calling，但要兼容不支持 function calling 的模型。

### 15.3 Tool Adapter

目标：让 HelloAgents 能调用 HyperAgents ToolManager。

思路：

```text
HelloAgents Tool
    ↓ execute(args)
HyperAgents ToolManager.execute_tool(...)
    ↓
ToolExecutionResult
    ↓
HelloAgents ToolResponse
```

不要复制 Tool 逻辑。Tool/MCP/Skill/Knowledge 的事实来源仍然是 HyperAgents。

### 15.4 Event Adapter

目标：让前端无需大改。

HelloAgents 内部事件映射到：

```text
thought -> AgentEvent(stage="thought")
action -> AgentEvent(stage="action")
tool_result -> AgentEvent(stage="observation")
final -> AgentEvent(stage="final_answer")
error -> AgentEvent(stage="final_answer", error=...)
```

### 15.5 Runner

统一输出：

```python
@dataclass
class AgentEngineResult:
    text: str
    events: list[dict]
    used_tools: list[str]
    used_skills: list[str]
    used_knowledge_bases: list[str]
    artifacts: list[dict]
```

## 16. 阶段 3：A/B 测试矩阵

必须用真实案例比较，而不是凭感觉判断。

### 16.1 Agent Engine 对比

| Case | legacy | current react | hello_react |
|---|---|---|---|
| 普通问答 | ✅ | ✅ | 待测 |
| MCP 工具调用 | 部分依赖 function calling | ✅ | 待测 |
| Skill listing | ✅ | ✅ | 待测 |
| xlsx 生成文件 | 不稳定 | 不稳定 | 待测 |
| xlsx 修改源文件 | 不稳定 | 改进中 | 待测 |
| front-design 生成 HTML | 效果一般 | 效果一般 | 待测 |
| Knowledge 问答 | ✅ | 需确认 | 待测 |
| Workflow step | ✅ | ✅ | 第二阶段 |

### 16.2 xlsx Skill 测试

测试任务：

```text
使用 xlsx skill 帮我把 uploads/.../xlsx_skill_rich_one_sheet.xlsx 中的空白列删掉，另存为新的 xlsx 文件
```

验收标准：

- 必须读取源文件。
- 必须识别真正空白列。
- 必须输出新文件到 My Files。
- 输出文件不得与源文件完全一致。
- RuntimeRunEvent 中能看到 Skill load、script execute、artifact saved。

### 16.3 front-design Skill 测试

测试任务：

```text
使用 front-design skill 帮我生成一个卖猫粮产品的网站首页，要温馨好看
```

验收标准：

- 必须加载完整 SKILL.md。
- 必须生成可下载 HTML 文件。
- HTML 中应有完整视觉结构，而不是简单模板。
- My Files 中保存生成文件。
- 回答中只提示文件路径，不贴长 HTML。

### 16.4 MCP 测试

测试任务：

```text
调用已绑定 MCP 查询可用工具，并执行一个工具调用
```

验收标准：

- MCP tools 正确加载。
- 工具调用参数正确。
- 错误能记录到 trace。

## 17. 对 Workflow 的特别分析

Workflow 是 HyperAgents 和 HelloAgents 关系中最微妙的一部分。

HelloAgents 提供 multi-agent / sub-agent / plan-solve 思路，而 HyperAgents 已经有自己的 Workflow Resource 和 Workflow Engine。

因此不建议让 HelloAgents 接管 HyperAgents Workflow。更合理的是：

```text
HyperAgents Workflow Engine 仍然负责：
  - workflow definition
  - graph routing
  - run history
  - step execution
  - DB persistence

HelloAgents 可作为某个 step 内部的 Agent Engine：
  - hello_react
  - hello_plan_solve
  - hello_reflection
```

也就是说，HelloAgents 不替代 Workflow，而是成为 Workflow 节点的一种执行模式。

未来节点可以是：

```json
{
  "id": "writer",
  "agent_id": "...",
  "engine_type": "hello_react",
  "input": {"text": "..."}
}
```

或者：

```json
{
  "id": "planner",
  "agent_id": "...",
  "engine_type": "hello_plan_solve",
  "input": {"text": "..."}
}
```

## 18. 对 Skills 的特别分析

Skills 是当前最需要改善的模块。HelloAgents 对 Skills 的支持可以借鉴，但必须注意：HyperAgents 的 Skill 不是普通 Python function，它是 Resource。

HyperAgents Skill 特点：

- 项目资源。
- 可上传 Skill 包。
- 有 `SKILL.md`。
- 可带 scripts/templates。
- 可绑定 Agent。
- 需要保存输出到 My Files。
- 需要被 Workbench 和 Workflow 同时使用。

因此不能简单用 HelloAgents Skill 替换 HyperAgents Skill。

正确做法：

1. 保持 HyperAgents Skill 数据模型。
2. 保持 Skill upload / metadata / binding。
3. 将 HyperAgents Skill 暴露为 HelloAgents Tool。
4. Tool 执行时调用 HyperAgents SkillRuntime / SkillCodeRunner。
5. 将结果包装为 ToolExecutionResult / ToolResponse。

## 19. 对 MCP 的特别分析

HyperAgents 目前 MCP 已经是 Resource，并支持 probe/test。HelloAgents 也关注 MCP，但不应让 HelloAgents 直接管理 MCP 配置。

原因：

- MCP 的 endpoint/stdio/env/header 都已经存在 HyperAgents Resource config。
- 前端有 MCP 页面。
- Agent 绑定 MCP 用的是 project resource。
- RuntimeRunEvent 已经记录 MCP 使用。

正确做法：

- MCP client 仍由 HyperAgents 管理。
- HelloAgents ToolRegistry 中注册 MCP tools 的代理工具。
- MCP result 转成统一 ToolExecutionResult。

## 20. 对 Knowledge 的特别分析

HelloAgents 的 memory/context 思路可以借鉴，但 HyperAgents 的 Knowledge Base 是独立模块。

不建议替换：

- knowledge_documents
- document_chunks
- pgvector retrieval
- agent_knowledge_bindings

建议增强：

- Knowledge retrieval 结果统一为 ToolExecutionResult。
- ContextBuilder 统一安排 Knowledge chunk 的 token budget。
- Workflow step 可以显式声明是否使用 Knowledge。

## 21. 对前端的影响

如果采用方案 C/D，前端影响可控。

### 21.1 Workbench

可新增显示：

- Engine type: legacy / react / hello_react
- Tool trace
- Skill trace
- Artifacts
- Context summary

### 21.2 Resource Detail

Agent Detail 可以展示：

- Engine type
- Bound Tools / Skills / MCPs / Knowledge Bases
- Used In Workflows
- Last run status

### 21.3 Workflow Detail

Run history 可以展示：

- Step engine type
- Step trace
- Tool calls
- Artifacts

不建议前端第一阶段大改，先保证后端事件仍兼容当前 UI。

## 22. 风险清单 / Risk Register

| 风险 | 描述 | 缓解 |
|---|---|---|
| 依赖风险 | HelloAgents 版本变化导致接口不稳定 | Adapter 隔离，锁版本 |
| Provider 冲突 | HelloAgents 默认 LLM 配置绕过 HyperAgents provider | 必须使用 HyperAgents LLMService adapter |
| Tool 协议冲突 | HelloAgents Tool 与 HyperAgents ToolManager 模型不同 | Tool adapter + ToolExecutionResult |
| Skill 语义冲突 | 两边都有 Skill 概念，但数据模型不同 | HyperAgents Skill 为事实来源 |
| Event 不兼容 | 前端依赖当前 event 格式 | Event adapter 统一输出 AgentEvent |
| Workflow 复杂化 | Workflow 自身还在建设，引入新 engine 增加复杂度 | 先 Workbench A/B，后 Workflow 接入 |
| 调试难度增加 | 多 engine 并存难排查 | engine_type 显式记录到 RuntimeRunEvent |
| 安全边界 | Skill scripts 和 tool execution 有执行风险 | 延续现有 SkillRuntime sandbox / audit 策略 |

## 23. 建议的代码边界

新增或改造建议：

```text
backend/app/runtime/agent_engine/
  base.py                       # AgentEngine interface
  result.py                     # ToolExecutionResult / AgentEngineResult
  trace.py                      # TraceEvent schema
  context_builder.py            # ContextBundle builder
  hello_agents_adapter/
    __init__.py
    llm_adapter.py
    tool_adapter.py
    event_adapter.py
    runner.py
```

保留：

```text
llm_wrapper.py
react_agent.py
tool_manager.py
```

至少在两个版本周期内不要删除旧 engine。

## 24. 验收标准 / Acceptance Criteria

### 24.1 第一阶段验收

- ToolExecutionResult 接入 SkillTool / MCPTool / BuiltinTool。
- xlsx 修改文件任务能记录 artifact。
- front-design 生成 HTML 能保存到 My Files。
- RuntimeRunEvent 能看到 skill load / skill execute / artifact saved。
- 不影响 legacy/react 现有路径。

### 24.2 第二阶段验收

- 支持 `engine_type=hello_react`。
- 可在单个 Agent 上选择 hello_react。
- hello_react 能调用 load_skill。
- hello_react 能调用 xlsx/front-design Skill。
- hello_react events 能显示在 Workbench run history。
- 出错时能 fallback 到当前 react 或明确返回错误。

### 24.3 第三阶段验收

- Workflow step 支持指定 engine_type。
- hello_react step 能正常写入 workflow_step_executions。
- Run History 能查看 hello_react trace。
- 分支 Workflow 不受影响。

## 25. 最终建议 / Final Recommendation

结合 HyperAgents 当前状态，建议如下：

1. 不直接整体替换当前 Agent Engine。
2. 不单独替换 `LangChainLLMWrapper`，收益很小。
3. 第一优先级：引入统一 ToolExecutionResult / TraceEvent / ContextBuilder。
4. 第二优先级：新增 HelloAgents Adapter，作为 `engine_type=hello_react` 并行实验。
5. 第三优先级：用 xlsx、front-design、MCP、Knowledge 做 A/B 测试。
6. 如果 hello_react 明显更好，再考虑接入 PlanSolve / Reflection。
7. Workflow 不交给 HelloAgents 接管，只允许 HelloAgents 成为某个 step 的 engine。
8. HyperAgents 的 Project-first Resource 模型必须保持为系统主干。

一句话总结：

> HelloAgents 很适合做 HyperAgents 的 Agent Engine 参考实现和实验性执行后端，但不应该替代 HyperAgents 的 Project / Resource / Skill / Workflow / File 基础设施。最好的路线是 Adapter 并行验证，逐步吸收其优秀设计。