# HyperAgents Agent Framework Redesign (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md)

---

## 0) 摘要 / Executive Summary

中文：
本文档规划了 HyperAgents Agent 框架的重设计方案。当前实现依赖 LLM 模型的 Function Calling 能力，导致 GLM-5.1 等模型无法调用工具。新方案采用 **ReAct（Reasoning + Acting）模式** 结合 **LangChain 框架**，使任何 OpenAI 兼容模型都能驱动 Agent，并提升可观测性和工具复用率。

English:
This document outlines the redesign of HyperAgents Agent framework. Current implementation relies on LLM function calling capability, preventing models like GLM-5.1 from using tools. New proposal adopts **ReAct (Reasoning + Acting) pattern** with **LangChain framework**, enabling any OpenAI-compatible model to power agents, improving observability and tool reusability.

---

## 1) 当前问题分析 / Current Problem Analysis

### 1.1 功能限制 / Functional Limitations

中文：
- **模型依赖性强**：只有支持 function calling 的模型才能调用工具（如 GPT-4o、GPT-4-turbo）
- **无法用 GLM-5.1**：智谱清言 5.1 虽然功能强大，但不支持 function calling
- **可观测性弱**：无法看到 Agent 的推理过程（Thought），只能看到最终答案
- **工具调用单一**：依赖模型主动请求工具，模型不想调用就不调用

English:
- **Strong model dependency**: only models with function calling support (e.g., GPT-4o, GPT-4-turbo) can use tools
- **Cannot use GLM-5.1**: Zhipu GLM-5.1 lacks function calling capability
- **Weak observability**: cannot see agent reasoning process (Thought), only final answer
- **Single tool invocation pattern**: relies on model proactively requesting tools

### 1.2 用户期望 / User Expectation

中文：
用户希望无论用什么模型（只要支持 OpenAI 兼容格式），Agent 都能：
1. 自动分析用户意图
2. 主动选择合适的工具（MCP、Tools、Skills、Knowledge Base）
3. 调用工具获取信息
4. 整合信息后给出最终答案
5. **完整记录每一步推理过程**

English:
Users expect that regardless of model (as long as OpenAI-compatible), Agent can:
1. Auto-analyze user intent
2. Proactively select appropriate tools (MCP, Tools, Skills, Knowledge Base)
3. Call tools to retrieve information
4. Synthesize results for final answer
5. **Fully record each reasoning step**

---

## 2) 解决方案设计 / Solution Design

### 2.1 核心理念 / Core Concept

中文：
**Agent as Orchestrator**（Agent 作为编排器）

Agent 不再依赖模型的 function calling，而是：
1. 作为中央协调器（Orchestrator）
2. 接收用户输入
3. 使用 ReAct 模式（Thought → Action → Observation → Repeat）
4. 主动调用各种工具
5. 记录完整的思考和行动步骤

English:
**Agent as Orchestrator**

Agent no longer relies on model function calling. Instead:
1. Act as central coordinator
2. Receive user input
3. Use ReAct pattern (Thought → Action → Observation → Repeat)
4. Proactively invoke various tools
5. Record complete thought and action steps

### 2.2 架构设计 / Architecture Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3)                             │
│                                                                   │
│  Workbench: Chat + Run Timeline (with Thought/Action/Observation)│
└─────────────────────────────────────────────────────────────────┘
                             ↓ HTTP API
┌─────────────────────────────────────────────────────────────────┐
│                Backend (FastAPI)                                 │
├─────────────────────────────────────────────────────────────────┤
│  Chat API                                                         │
│    ├─ parse user query                                           │
│    ├─ retrieve memory (context)                                  │
│    └─ delegate to Agent Engine                                   │
├─────────────────────────────────────────────────────────────────┤
│  Agent Engine (LangChain-based)                                  │
│    ├─ Agent Executor (ReAct Loop)                               │
│    │   ├─ Thought: LLM reasoning                                 │
│    │   ├─ Action: select & invoke tool                           │
│    │   └─ Observation: process result                            │
│    │                                                              │
│    ├─ Tool Manager                                               │
│    │   ├─ MCP Tools (dynamic from endpoint)                      │
│    │   ├─ Built-in Tools (search, calc, etc.)                   │
│    │   ├─ Skills (composite tools)                               │
│    │   └─ Knowledge Base Tools (retrieval)                       │
│    │                                                              │
│    ├─ Model Router                                               │
│    │   ├─ OpenAI Compatible Provider                            │
│    │   ├─ LangChain LLM Wrapper                                 │
│    │   └─ Model Selection (config-driven)                       │
│    │                                                              │
│    └─ Memory Manager                                             │
│        ├─ Hybrid Search (Vector + BM25)                         │
│        └─ Context Window Management                              │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Runtime & Persistence                                            │
│    ├─ RuntimeRun (execution lifecycle)                           │
│    ├─ RuntimeRunEvent (Thought/Action/Observation timeline)     │
│    └─ PostgreSQL + pgvector                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 ReAct 模式详解 / ReAct Pattern Explained

中文：
ReAct = Reasoning + Acting

一个典型的 Agent 执行流程：

```
User Input: "查询成都今天天气，并根据天气建议是否需要带伞"

┌─ Step 1: Thought ─────────────────────────────────────────┐
│ 我需要先查询成都的天气情况。我可以调用 testgaode MCP      │
│ 中的 weather 工具。                                        │
└───────────────────────────────────────────────────────────┘
        ↓
┌─ Step 2: Action ──────────────────────────────────────────┐
│ Tool: call_mcp("testgaode", "weather")                     │
│ Input: {"location": "chengdu"}                             │
└───────────────────────────────────────────────────────────┘
        ↓
┌─ Step 3: Observation ─────────────────────────────────────┐
│ Result: {                                                  │
│   "location": "成都",                                      │
│   "temperature": 18,                                       │
│   "condition": "阴有小雨",                                 │
│   "humidity": 75                                           │
│ }                                                          │
└───────────────────────────────────────────────────────────┘
        ↓
┌─ Step 4: Thought ─────────────────────────────────────────┐
│ 根据查询结果，成都今天阴有小雨，温度 18℃。               │
│ 下雨了所以应该建议带伞。天气较凉，可能需要加衣。          │
│ 我现在有足够信息给出最终建议。                             │
└───────────────────────────────────────────────────────────┘
        ↓
┌─ Step 5: Final Answer ────────────────────────────────────┐
│ 成都今天阴有小雨，气温 18℃，建议：                        │
│ 1. 带上伞或雨衣                                            │
│ 2. 穿上外套或毛衣保暖                                      │
│ 3. 避免长时间在户外                                        │
└───────────────────────────────────────────────────────────┘
```

English:
A typical Agent execution flow:

Same pattern applies in English with weather query for London, etc.

### 2.4 工具统一定义 / Unified Tool Definition

中文：
所有工具（MCP、Tools、Skills、KB）统一为 JSON Schema 格式：

```json
{
  "name": "weather",
  "description": "查询城市实时天气信息",
  "parameters": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "城市名称，e.g. '成都', '北京'"
      },
      "unit": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "default": "celsius"
      }
    },
    "required": ["location"]
  }
}
```

英文说明同上。

---

## 3) 实施路线图 / Implementation Roadmap

### 3.1 Phase 1: 基础框架 (1-2 weeks)

#### 任务 / Tasks:

1. **集成 LangChain 依赖** (1-2 days)
   - Add `langchain`, `langchain-openai`, `langchain-community` to `requirements.txt`
   - Create `backend/app/runtime/agent_engine/` directory structure

2. **Model Router 改造** (2-3 days)
   - Create `LangChainLLMWrapper` to adapt existing providers (OpenAI, localhost) to LangChain interface
   - Support model selection from Agent config

3. **Agent Base 类** (2-3 days)
   - Implement `ReActAgent` class (thought → action → observation loop)
   - Support max iterations, timeout, error handling
   - Event recording for each step

4. **工具加载器** (1-2 days)
   - `ToolLoader` to dynamically load MCP, built-in, skills tools
   - Unified tool schema extraction

#### Deliverables:
- `backend/app/runtime/agent_engine/__init__.py`
- `backend/app/runtime/agent_engine/llm_wrapper.py`
- `backend/app/runtime/agent_engine/react_agent.py`
- `backend/app/runtime/tool_manager.py`
- Tests in `backend/tests/test_agent_engine.py`

---

### 3.2 Phase 2: 工具适配 (1 week)

#### 任务 / Tasks:

1. **MCP Tools 适配** (2-3 days)
   - `MCPTool` class extending LangChain `Tool`
   - Dynamic tool discovery from MCP endpoints
   - Error handling and result normalization

2. **Built-in Tools** (1-2 days)
   - Web search tool (using MCP or external API)
   - Calculator tool
   - Time/date tool
   - Text processing tools

3. **Skills 作为 Composite Tool** (2 days)
   - Skills = 组合多个工具的高阶操作
   - Skill workflow definition

4. **Knowledge Base Tool** (1-2 days)
   - `KBRetrieval` tool using hybrid search (vector + BM25)
   - Context window aware retrieval

#### Deliverables:
- `backend/app/runtime/tools/mcp_tool.py`
- `backend/app/runtime/tools/builtin_tools.py`
- `backend/app/runtime/tools/skill_executor.py`
- `backend/app/runtime/tools/kb_tool.py`

---

### 3.3 Phase 3: Chat API 集成 (3-5 days)

#### 任务 / Tasks:

1. **改造 Chat Handler** (2-3 days)
   - Replace existing executor with Agent Engine
   - Pass MCPs, Tools, Skills, KB to Agent
   - Handle Agent output and errors

2. **RuntimeRun Event 扩展** (1-2 days)
   - Add `agentic_stage` field: `thought` / `action` / `observation` / `final_answer`
   - Store each step's content and metadata

3. **测试与验证** (1 day)
   - End-to-end test with multiple models (GLM-5.1, GPT-4o, Ollama)
   - Verify all tool types work (MCP, built-in, skills, KB)

#### Deliverables:
- Updated `backend/app/api/v1/chat.py`
- Updated `backend/app/db/models.py` (RuntimeRunEvent schema)
- Integration tests

---

### 3.4 Phase 4: 前端显示与文档 (1 week)

#### 任务 / Tasks:

1. **Workbench 增强** (2-3 days)
   - Display Thought → Action → Observation steps in Run Timeline
   - Collapsible cards for each agentic step
   - Show tool calls, inputs, outputs

2. **完整文档** (2-3 days)
   - API 文档（Agent 配置、工具定义）
   - 用户指南（如何配置 Agent）
   - 开发者指南（如何新增工具类型）
   - 架构设计文档

3. **示例代码与演示** (1-2 days)
   - Example agents for common scenarios
   - Demo video or screenshots

#### Deliverables:
- Updated `frontend/src/views/WorkbenchView.vue`
- Comprehensive docs in `docs/design/agent-implementation.md`
- Tutorial and examples

---

## 4) 核心模块详设 / Core Module Designs

### 4.1 ReActAgent 实现伪代码 / ReActAgent Pseudo-code

```python
class ReActAgent:
    def __init__(self, llm, tools, max_iterations=10):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.max_iterations = max_iterations
    
    def run(self, user_input, context=None):
        """Execute ReAct loop."""
        messages = [{"role": "user", "content": user_input}]
        events = []
        
        for i in range(self.max_iterations):
            # Step 1: Thought - LLM reasoning
            thought_prompt = self._build_thought_prompt(messages, user_input)
            thought = self.llm.generate(thought_prompt)
            events.append({
                "stage": "thought",
                "iteration": i,
                "content": thought
            })
            
            # Step 2: Action - Parse action from LLM response
            action = self._parse_action(thought)
            if action is None or action["type"] == "final_answer":
                # Agent decided to finish
                final_answer = self._extract_final_answer(thought)
                events.append({
                    "stage": "final_answer",
                    "content": final_answer
                })
                return final_answer, events
            
            events.append({
                "stage": "action",
                "iteration": i,
                "tool_name": action["tool"],
                "input": action["input"]
            })
            
            # Step 3: Observation - Execute tool
            try:
                result = self.tools[action["tool"]].invoke(action["input"])
                observation = str(result)
                events.append({
                    "stage": "observation",
                    "iteration": i,
                    "tool_name": action["tool"],
                    "result": observation
                })
                # Add observation to messages for next iteration
                messages.append({"role": "assistant", "content": thought})
                messages.append({"role": "user", "content": f"Tool result: {observation}"})
            except Exception as e:
                # Tool error - ask LLM to handle
                error_msg = f"Tool {action['tool']} failed: {str(e)}"
                events.append({
                    "stage": "observation",
                    "iteration": i,
                    "error": error_msg
                })
                messages.append({"role": "user", "content": error_msg})
        
        # Max iterations reached
        final_answer = "无法在规定步数内解决问题"
        events.append({
            "stage": "final_answer",
            "type": "max_iterations_reached",
            "content": final_answer
        })
        return final_answer, events
```

### 4.2 Model Router 设计 / Model Router Design

```python
class ModelRouter:
    """Route requests to appropriate LLM provider."""
    
    def __init__(self, providers: dict):
        self.providers = providers  # {name: LangChain LLM instance}
    
    def get_llm(self, agent_config: dict):
        """Select LLM based on agent config."""
        model_provider = agent_config.get("model_provider", "openai")
        model_name = agent_config.get("model_name", "gpt-4o-mini")
        provider_profile = agent_config.get("provider_profile")
        
        # Route to appropriate provider
        if model_provider == "openai":
            return ChatOpenAI(
                model=model_name,
                temperature=0.2,
                api_key=self._get_api_key(provider_profile or "openai")
            )
        elif model_provider == "localhost":
            return ChatOpenAI(
                model=model_name,
                base_url="http://localhost:11434/v1",
                api_key="not-needed"
            )
        # ... more providers
```

### 4.3 Tool Manager 设计 / Tool Manager Design

```python
class ToolManager:
    """Manage all tool types (MCP, built-in, skills, KB)."""
    
    def load_tools(self, agent_config: dict, context: dict):
        """Load tools for an agent."""
        tools = []
        
        # 1. MCP Tools
        mcp_ids = agent_config.get("mcp_ids", [])
        for mcp_id in mcp_ids:
            mcp_spec = context["mcps"][mcp_id]
            mcp_tools = self._load_mcp_tools(mcp_spec)
            tools.extend(mcp_tools)
        
        # 2. Built-in Tools
        builtin_names = agent_config.get("builtin_tools", [])
        tools.extend(self._load_builtin_tools(builtin_names))
        
        # 3. Skills
        skill_ids = agent_config.get("skill_ids", [])
        for skill_id in skill_ids:
            skill_tool = self._load_skill_tool(skill_id, context)
            tools.append(skill_tool)
        
        # 4. Knowledge Base Tool
        if agent_config.get("knowledge_base_ids"):
            kb_tool = self._load_kb_tool(agent_config, context)
            tools.append(kb_tool)
        
        return tools
    
    def _load_mcp_tools(self, mcp_spec):
        """Dynamically load tools from MCP endpoint."""
        client = get_mcp_client(mcp_spec)
        mcp_tools = client.list_tools()
        return [MCPTool(mcp_spec, tool_def) for tool_def in mcp_tools]
```

---

## 5) 数据库模型扩展 / Database Schema Extensions

中文：
在现有的 `RuntimeRunEvent` 基础上扩展，记录 Agentic Step：

```python
class RuntimeRunEvent(Base):
    __tablename__ = "runtime_run_events"
    
    id: str  # 主键
    run_id: str  # RuntimeRun 外键
    stage: str  # "runtime" / "agent" / "thought" / "action" / "observation" / "final_answer"
    status: str  # "running" / "succeeded" / "failed"
    iteration: int | None  # Agentic 循环迭代号 (null for non-agentic stages)
    
    # Agentic-specific fields
    tool_name: str | None  # 被调用的工具名
    tool_input: JSON | None  # 工具输入参数
    tool_result: JSON | None  # 工具返回结果
    thought_content: str | None  # 思考内容
    
    # General fields
    message: str  # 事件描述
    payload: JSON  # 其他元数据
    created_at: datetime
```

English:
Same structure but in English field descriptions.

---

## 6) 迁移策略 / Migration Strategy

### 6.1 向后兼容 / Backward Compatibility

中文：
- 新的 Agent Engine 与旧的 executor 并存
- Agent config 新增 `engine_type` 字段：`"legacy"` 或 `"react"`
- 旧的 Agent 继续用旧引擎，新 Agent 用 ReAct 引擎
- 逐步迁移，无需一次性切换

English:
- New Agent Engine coexists with old executor
- Add `engine_type` to Agent config: `"legacy"` or `"react"`
- Old agents use legacy engine, new agents use ReAct
- Gradual migration, no hard cutover

### 6.2 从现有系统升级 / Upgrade Path

```
Current State:
- Agent with run_mode="llm"
- Executor calls LLM directly

New State:
- Agent with run_mode="llm" + engine_type="react"
- Chat API creates ReActAgent
- Agent runs ReAct loop
- Each step recorded as RuntimeRunEvent
```

---

## 7) 成功标准 / Success Criteria

### 7.1 功能要求 / Functional Requirements

- ✅ GLM-5.1 等模型也能调用 MCP 工具
- ✅ 用户能看到 Agent 的完整思考过程（Thought/Action/Observation）
- ✅ 支持多轮工具调用（一个用户问题需要调用多个工具）
- ✅ 支持工具调用失败与重试
- ✅ 支持所有工具类型（MCP、Tools、Skills、KB）

### 7.2 性能指标 / Performance Metrics

- 平均 Agent 执行时间 < 10 秒（不含网络延迟）
- 单个 Agent 最大迭代数 10（防止无限循环）
- 支持 100+ 并发 Agent 运行

### 7.3 可观测性 / Observability

- 每个 agentic step 都有时间戳和事件记录
- 完整的错误堆栈跟踪
- 可导出执行轨迹为 JSON

---

## 8) 风险与缓解 / Risks & Mitigations

| 风险 | 影响 | 缓解 |
|-----|------|------|
| LangChain 版本更新 | 代码兼容性 | 创建抽象层，定期测试 |
| LLM 生成无效 action | Agent 失败 | 实现 action parser 容错，最多重试 3 次 |
| 工具调用超时 | 用户体验差 | 设置工具调用超时 30 秒，返回超时错误 |
| 学习成本 | 开发效率 | 详细文档 + 示例代码 |
| 第三方依赖重 | 维护负担 | 评估轻量化替代方案 |

---

## 9) 参考资源 / References

- LangChain Docs: https://python.langchain.com/
- ReAct Paper: https://arxiv.org/abs/2210.03629
- OpenAI Function Calling: https://platform.openai.com/docs/guides/function-calling
- MCP Spec: https://modelcontextprotocol.io/

---

## 10) 下一步行动 / Next Steps

1. **评审本文档**（1 day）
   - 团队讨论、反馈、确认方向

2. **环境准备**（1 day）
   - LangChain 依赖评估
   - 开发环境设置

3. **启动 Phase 1**
   - 按照路线图逐步实施

---

**文档版本**: v0.1.0  
**最后更新**: 2026-07-13  
**所有者**: HyperAgents Team
## English Companion Summary

This design note describes a future-oriented redesign of the Agent framework. The goal is to move from scattered execution paths toward a unified Agent runtime that can plan, call tools, retrieve knowledge, activate Skills, and expose clear observability.

Key ideas:

1. Separate Agent definition, runtime execution, tool management, memory/knowledge access, and provider adapters into clearer modules.
2. Support ReAct-style loops where the Agent can think, choose an action, call a tool/MCP/Skill, observe the result, and continue until a final answer is ready.
3. Keep structured runtime events so users can inspect which Agent ran, which tool was called, what failed, and why.
4. Make Tool, MCP, Knowledge, and Skill behavior reusable through project-scoped bindings instead of one-off prompt logic.
5. Improve safety through controlled execution boundaries, audit records, timeouts, and explicit configuration.

Implementation status note:

Some ideas from this redesign have already landed, especially ReAct support, Tool/MCP loading, Skill activation, and runtime events. Treat this document as architectural background; use module docs and code-api-map for current behavior.
