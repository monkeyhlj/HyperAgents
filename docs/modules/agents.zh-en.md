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

## 5. Advanced Config Examples / Advanced Config 示例

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

- 当前 `Custom Code` 运行于受限子进程中，不支持任意导入模块。
- 禁止 `import`、`with`、`raise`、`global`、`nonlocal` 等语法。
- 更适合写轻量路由、规则判断、格式整理、简单工具编排前置逻辑。
- 如果你的逻辑已经复杂到需要大量依赖或外部 IO，更适合沉到 Tool / MCP / 后端服务实现。

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

## 10. File Path / 文档路径

- Workspace path: `docs/modules/agents.zh-en.md`
- MkDocs nav: `Module Docs -> Agents`
