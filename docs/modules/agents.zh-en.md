# Agents Module Guide / Agents 模块说明

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [Frontend Guide](../guides/frontend-guide.zh-en.md)

## 1. Purpose / 作用

中文：
资源编辑页里的 `Custom Code (Editable)` 和 `Advanced Config JSON (Editable)` 是给 Agent 作者使用的两块核心区域。

- `Custom Code` 用来定义 `run_mode=code` 时 Agent 的执行逻辑。
- `Advanced Config JSON` 用来补充结构化运行参数，例如角色名、温度、业务标记、路由规则、实验开关等。

English:
The two key authoring areas in the resource edit page are `Custom Code (Editable)` and `Advanced Config JSON (Editable)`.

- `Custom Code` defines the execution logic when `run_mode=code`.
- `Advanced Config JSON` carries structured runtime parameters such as role names, temperature, feature flags, routing hints, or business-specific settings.

## 2. When Each Field Is Used / 什么时候会生效

### Custom Code

中文：
只有当 `Agent Run Mode` 选择为 `code` 时，`Custom Code` 才会被运行。后端会在隔离子进程中执行它，并尝试按下面的优先级读取结果：

1. `run(input_text, context)`
2. `agent_main(input_text, context)`
3. `RESULT`

English:
`Custom Code` is executed only when `Agent Run Mode` is set to `code`. The backend runs it in an isolated subprocess and resolves the result in this order:

1. `run(input_text, context)`
2. `agent_main(input_text, context)`
3. `RESULT`

### Advanced Config JSON

中文：
这块 JSON 会被合并进 resource 的 `config`。在 `Dialog Test` 和真正保存后的运行中，都会进入 `context["config"]`。

English:
This JSON is merged into the resource `config`. Both `Dialog Test` and saved runtime execution expose it through `context["config"]`.

## 3. Context Shape / context 结构

在 `Custom Code` 中，你通常会拿到：

```python
context = {
		"project_id": "...",
		"user_id": "...",
		"config": {
				"tool_ids": [...],
				"skill_ids": [...],
				"mcp_ids": [...],
				"knowledge_base_ids": [...],
				"role_name": "Code Agent",
				"temperature": 0.2,
				"...": "..."
		}
}
```

说明：

- `project_id`: 当前项目 ID。
- `user_id`: 当前用户 ID。
- `config`: 资源运行配置，包含 UI 上勾选的关联资源，以及你在 Advanced Config JSON 中填写的额外参数。

## 4. Recommended Pattern / 推荐写法

推荐把代码写成一个纯函数：

```python
def run(input_text, context):
		text = input_text.strip()
		config = context.get("config", {})
		role_name = config.get("role_name", "Code Agent")

		if not text:
				return "请输入内容。"

		if "帮助" in text:
				return (
						f"我是 {role_name}。\n"
						"你可以问我：\n"
						"1. 当前项目\n"
						"2. 当前用户\n"
						"3. 回显: 任何内容"
				)

		if "当前项目" in text:
				return f"当前项目 ID: {context.get('project_id', '-')}"

		if "当前用户" in text:
				return f"当前用户 ID: {context.get('user_id', '-')}"

		return f"{role_name} 回复：{text}"
```

为什么推荐这种写法：

- 输入和输出都清晰。
- 依赖只来自 `input_text` 和 `context`，容易测试。
- 能快速从低代码配置过渡到正式代码。

### Tool call pattern in code mode / code 模式下调用 Tool

中文：
当前版本里，Agent 要调用 Tool，需要把 Agent 切到 `run_mode=code`，然后在 `Custom Code` 中显式调用 `call_tool(...)`。

English:
In the current version, an Agent can call a Tool only in `run_mode=code`, and the `Custom Code` must explicitly call `call_tool(...)`.

可用辅助函数 / Available helpers:

- `call_tool(tool_name, input_data)`：按 Tool 名称执行一个已关联的 Tool
- `list_tools()`：返回当前 Agent 关联的 Tool 名称列表

示例 / Example:

```python
def run(input_text, context):
	text = input_text.strip()

	if text == "ping":
		return call_tool("testping", {"action": "ping", "text": text})

	if text == "show config":
		return {
			"project_id": context.get("project_id"),
			"tool_ids": context.get("config", {}).get("tool_ids", []),
			"tools": list_tools(),
		}

	return {"echo": text}
```

说明 / Notes:

- `tool_name` 要和 Tool 资源的 `name` 一致，比如 `testping`
- 只有当前 Agent 关联到 `tool_ids` 中的 Tool 才能被调用
- 当前仅支持 `python` Tool runtime
- 可用内置模块：`json`、`re`（无需 import，直接使用）

### Hybrid mode: Tools + LLM fallback / 混合模式：工具+LLM回退

中文：
如果你希望 code-mode Agent 在某些场景用工具计算，其他场景则由大模型处理，可以使用混合模式。

做法：

1. 在 Custom Code 中，对数学问题或特定操作调用 `call_tool(...)`。
2. 对于无法处理的问题，返回 `{"use_llm": True}`。
3. Backend 会自动检测这个标记，并调用配置的 LLM 模型来处理原始输入。

完整示例 / Full example:

```python
def run(input_text, context):
    text = input_text.strip()
    
    # 检测是否是数学运算问题
    math_keywords = ["加", "+", "减", "-", "乘", "*", "除", "/", "等于", "=", "算", "计算"]
    is_math_question = any(keyword in text for keyword in math_keywords)
    
    if is_math_question:
        # 提取数字
        numbers = re.findall(r'-?\d+\.?\d*', text)
        if len(numbers) >= 2:
            try:
                # 推断操作
                if "加" in text or "+" in text:
                    op = "add"
                elif "减" in text or "-" in text:
                    op = "subtract"
                elif "乘" in text or "*" in text:
                    op = "multiply"
                elif "除" in text or "/" in text:
                    op = "divide"
                else:
                    op = "add"
                
                # 调用工具
                result = call_tool("calculate", {
                    "operation": op,
                    "a": float(numbers[0]),
                    "b": float(numbers[1])
                })
                
                if result.get("ok"):
                    return {
                        "result": f"{numbers[0]}{op}{numbers[1]}等于{result.get('result', '')}"
                    }
                else:
                    return {"error": result.get("error")}
            except Exception as e:
                return {"error": f"计算失败: {str(e)}"}
    
    # 非数学问题，交给 LLM 处理
    return {"use_llm": True}
```

说明 / Notes:

- 返回 `{"use_llm": True}` 时，Backend 会自动使用 Agent 配置的 `model_provider` 和 `model_name` 调用 LLM。
- 如果 Agent 没有配置模型信息，LLM 回退会失败，返回错误。
- LLM 回复会通过 `system_prompt` 进行约束。
- 这种混合方式特别适合："规则+工具处理特定业务逻辑，通用问题交给大模型"。

工具使用情况显示 / Tool usage display:

- 当 code-mode Agent 调用了工具，Workbench 的 Conversation 中会显示一个**橙色标签**，标注调用的工具名。
- 如果使用了 LLM 回退（没有调用工具），标签不会出现。
- 这样可以清晰地看出每条回复是由工具处理还是由 LLM 处理。

## 5. Advanced Config Examples / Advanced Config 示例

### provider_profile is the key / provider_profile 是关键字段

中文：
`provider_profile` 用来告诉后端“这一份 Agent 配置应该读取哪一组环境变量前缀”。它比单纯写 `model_provider` 更重要，因为它决定了 `OPENAI_*`、`ZHIPU_*`、`QWEN_*` 这一类配置到底从哪一组 `.env` 变量加载。
`role_name` 只是一个可选的人类可读标签，用来给代码模式或提示词中的角色起名，不会影响 provider 选择。

English:
`provider_profile` tells the backend which env-variable prefix to read for this Agent configuration. It is more important than `model_provider` alone because it decides whether settings come from `OPENAI_*`, `ZHIPU_*`, `QWEN_*`, and similar `.env` entries.

常见映射 / Common mappings:

- `provider_profile: "openai"` -> `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_DEFAULT_MODEL`
- `provider_profile: "zhipu"` -> `ZHIPU_API_KEY`, `ZHIPU_BASE_URL`, `ZHIPU_DEFAULT_MODEL`
- `provider_profile: "qwen"` -> `QWEN_API_KEY`, `QWEN_BASE_URL`, `QWEN_DEFAULT_MODEL`

说明 / Note:

- 如果你写了 `provider_profile: "qwen"`，就要在 workspace 根目录 `.env` 里补齐 `QWEN_*` 变量。
- `model_provider` 只表示运行时客户端类型，比如 `openai` 或 `localhost`。
- `provider_profile` 决定读哪组凭据和默认模型。


### URL + API Key Provider Connection / 通过 URL + Key 添加模型

中文：
除了 `provider_profile` 读取 `.env` 的平台级配置，Agents 页面现在也支持项目级 Provider Connection：

1. 在 `Custom model settings` 中选择 `URL + API Key`。
2. 填写 OpenAI-compatible `Base URL` 与 `API Key`。
3. 点击 `Load Models`，后端会请求 `{base_url}/models` 并把模型列表返回给页面。
4. 选择模型后点击 `Test`，通过最小 chat completion 验证连接。
5. 点击 `Save Connection` 后，API Key 会加密保存到数据库，Agent 只保存 `provider_connection_id` 和所选 `model_name`。

English:
In addition to `.env`-backed `provider_profile`, the Agents page now supports project-level Provider Connections:

1. Choose `URL + API Key` under `Custom model settings`.
2. Fill an OpenAI-compatible `Base URL` and `API Key`.
3. Click `Load Models`; the backend calls `{base_url}/models` and returns model IDs to the page.
4. Select a model and click `Test` to verify with a minimal chat completion.
5. Click `Save Connection`; the API key is stored encrypted in the database, while the Agent stores only `provider_connection_id` and `model_name`.

说明 / Notes:

- 旧的 `Env profile` 方式仍然保留，适合平台级预置模型。
- 如果某个平台不支持 `/models`，可以手动输入 `model_name`，但仍建议用 `Test` 验证后再保存。
- 生产环境请设置 `PROVIDER_CONNECTION_SECRET_KEY`，并优先使用 Secret Manager/KMS 管理密钥。
### Example D: provider_profile-driven config

```json
{
	"provider_profile": "qwen",
	"role_name": "Qwen Agent",
	"temperature": 0.2
}
```

对应 `.env` 示例 / Matching `.env` example:

```dotenv
QWEN_API_KEY=your-key
QWEN_BASE_URL=https://your-qwen-compatible-endpoint/v1
QWEN_DEFAULT_MODEL=qwen-plus
```

### Example A: role_name and behavior flags

```json
{
	"role_name": "Support Agent",
	"temperature": 0.2,
	"reply_style": "concise",
	"features": {
		"show_help": true,
		"allow_project_echo": true
	}
}
```

### Example B: lightweight route table

```json
{
	"role_name": "Ops Agent",
	"routes": {
		"health": "system",
		"deploy": "ops",
		"cost": "finance"
	}
}
```

### Example C: prompt constants for code mode

```json
{
	"role_name": "QA Agent",
	"prompts": {
		"smoke": "请先给出 smoke test 清单",
		"regression": "请按模块列出回归风险"
	}
}
```

## 6. Reserved and Common Keys / 保留键与常用键

建议把这些字段继续放在表单专属区域，不要只写在 JSON 里：

- `run_mode`
- `system_prompt`
- `custom_code`
- `tool_ids`
- `skill_ids`
- `mcp_ids`
- `knowledge_base_ids`

原因：

- 它们已经有独立 UI。
- 用独立 UI 更容易被前端校验、保存和预览。
- JSON 更适合放“额外配置”，不是复制表单主字段。

## 7. How To Test / 如何测试

### Dialog Test in Resource Page

中文：

1. 先选中项目。
2. 选择 `Agent Run Mode = code`。
3. 编写 `Custom Code`。
4. 在 `Advanced Config JSON` 里写入例如 `role_name`。
5. 在左侧 `Dialog Test` 发送 `帮助`、`当前项目`、`当前用户` 等消息。

English:

1. Select a project first.
2. Set `Agent Run Mode = code`.
3. Write `Custom Code`.
4. Put values such as `role_name` into `Advanced Config JSON`.
5. Use `Dialog Test` on the left with prompts like `帮助`, `当前项目`, and `当前用户`.

### Suggested test cases / 建议测试项

1. Empty input returns a friendly fallback.
2. Help command returns menu text.
3. `role_name` from config changes the response text.
4. Project/user info can be read from `context`.
5. Invalid JSON should be rejected before preview or save.

## 8. Current Constraints / 当前限制

- 当前 `Custom Code` 运行于受限子进程中，不支持任意导入模块（仅支持白名单 import）。
- 禁止 `with`、`raise`、`global`、`nonlocal` 等语法。
- 更适合写轻量路由、规则判断、格式整理、简单工具编排前置逻辑。
- 如果你的逻辑已经复杂到需要大量依赖或外部 IO，更适合沉到 Tool / MCP / 后端服务实现。

补充（最新）/ Update:

- 目前已支持**受控 import**：允许导入白名单模块 `json`、`re`、`math`、`time`、`datetime`、`httpx`、`requests`。
- `requests` 在沙箱中映射到 `httpx` 兼容层（可用于常见 `get/post` 场景）。
- 白名单外模块会报错：`Import not allowed: <module>`。

## 9. Troubleshooting / 常见问题

### Q1. 为什么 `Dialog Test` 和保存后的行为不一致？

通常原因：

- `Advanced Config JSON` 格式不合法。
- `run_mode` 不是 `code`。
- 代码里没有定义 `run(...)` / `agent_main(...)` / `RESULT`。

### Q2. 为什么代码里读不到 `role_name`？

确认你是从下面读取：

```python
config = context.get("config", {})
role_name = config.get("role_name", "Code Agent")
```

### Q3. 什么时候用 `system_prompt`，什么时候用 `Custom Code`？

- 想让大模型按某种角色和话术回复，用 `system_prompt` + `llm`。
- 想自己控制分支、规则、返回结构，用 `custom_code` + `code`。

### Q4. 如何实现"部分用工具，部分用大模型"？

使用混合模式：在 `run_mode=code` 的 Custom Code 中，根据输入类型做判断。如果是你的工具能处理的，就 `call_tool(...)`；否则返回 `{"use_llm": True}`，Backend 会自动调用 LLM。

示例见上面的"Hybrid mode: Tools + LLM fallback"。

### Q5. 为什么 LLM 回退没有被触发？

可能原因：

- Agent 没有配置 `model_provider` 和 `model_name`。
- 返回值不是 `{"use_llm": True}` 的标准格式。
- 检查后端日志是否有错误提示。

### Q6. 工具调用标签在哪里显示？

在 Workbench 的 Conversation 区域，Assistant 的回复上方会显示一个**橙色标签**，表示调用的工具名。如果没有标签，说明这次回复没有调用工具（可能是直接返回结果或使用了 LLM 回退）。

## 10. File Path / 文档路径

- Workspace path: `docs/modules/agents.zh-en.md`
- MkDocs nav: `Module Docs -> Agents`
