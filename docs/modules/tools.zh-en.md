# Tools Module Guide / Tools 模块说明

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [Agents Guide](./agents.zh-en.md)

## 1. Purpose / 作用

中文：
Tool 资源用于封装可复用能力（计算、HTTP 请求、数据处理等），并由 Agent 在 code 模式通过 `call_tool(...)` 调用。

English:
Tool resources package reusable capabilities (calculation, HTTP requests, data processing, etc.) and are invoked by code-mode agents via `call_tool(...)`.

## 2. Runtime Contract / 运行契约

每个 Python Tool 需要实现：

```python
def run(input_data: dict, context: dict) -> dict:
	...
```

说明：

- `input_data`: 调用方传入参数。
- `context`: 运行上下文，包含项目/用户信息，以及 `tool` 元信息。
- 返回值建议为 JSON 可序列化的 `dict`。

## 3. How To Create / 创建方式

在资源编辑页创建 `kind=tool` 时，建议按下列字段填写：

1. `Tool Runtime`: `python`
2. `Function Name`: `run`
3. `Shared In Project`: `true`（推荐，便于同项目 Agent 复用）
4. 填写 `Tool Code`、`Input Schema JSON`、`Output Schema JSON`

## 4. Associate With Agent / 关联到 Agent

中文：

1. 编辑 Agent，设置 `Agent Run Mode = code`。
2. 在 `Associate Tools` 里勾选目标 Tool。
3. 在 `Custom Code` 中调用 `call_tool("tool_name", {...})`。

English:

1. Edit agent with `Agent Run Mode = code`.
2. Select target tools in `Associate Tools`.
3. Call `call_tool("tool_name", {...})` in `Custom Code`.

## 5. Controlled Import Rules / 受控 import 规则

当前沙箱支持白名单 import，允许模块：

- `json`
- `re`
- `math`
- `time`
- `datetime`
- `httpx`
- `requests`（映射到 `httpx` 兼容层）

说明：

- 白名单外 import 会报错：`Import not allowed: <module>`。
- 仍然禁止 `with`、`raise`、`global`、`nonlocal`。

## 6. Example A: Calculator Tool / 示例 A：算数工具

Tool code (copy-paste):

```python
def run(input_data, context):
	operation = str(input_data.get("operation") or "").strip().lower()
	a = float(input_data.get("a") or 0)
	b = float(input_data.get("b") or 0)

	if operation == "add":
		result = a + b
	elif operation == "subtract":
		result = a - b
	elif operation == "multiply":
		result = a * b
	elif operation == "divide":
		if b == 0:
			return {
				"ok": False,
				"error": "Division by zero",
				"operation": operation,
				"a": a,
				"b": b,
			}
		result = a / b
	else:
		return {
			"ok": False,
			"error": f"Unknown operation: {operation}",
			"supported": ["add", "subtract", "multiply", "divide"],
		}

	return {
		"ok": True,
		"operation": operation,
		"a": a,
		"b": b,
		"result": result,
	}
```

Input schema:

```json
{
  "type": "object",
  "properties": {
	"operation": { "type": "string" },
	"a": { "type": "number" },
	"b": { "type": "number" }
  },
  "required": ["operation", "a", "b"]
}
```

Output schema:

```json
{
  "type": "object",
  "properties": {
	"ok": { "type": "boolean" },
	"operation": { "type": "string" },
	"a": { "type": "number" },
	"b": { "type": "number" },
	"result": { "type": "number" },
	"error": { "type": "string" }
  }
}
```

## 7. Example B: HTTP Fetch Tool (with import) / 示例 B：HTTP 请求工具（含 import）

Tool code (copy-paste):

```python
def run(input_data, context):
	import requests

	url = str(input_data.get("url") or "http://127.0.0.1:8000/health").strip()
	method = str(input_data.get("method") or "GET").strip().upper()
	timeout = float(input_data.get("timeout") or 8)
	headers = input_data.get("headers") or {}
	params = input_data.get("params") or {}
	json_body = input_data.get("json") if isinstance(input_data, dict) else None

	try:
		if method == "GET":
			resp = requests.get(url, params=params, headers=headers, timeout=timeout)
		elif method == "POST":
			resp = requests.post(url, params=params, headers=headers, json=json_body, timeout=timeout)
		else:
			return {
				"ok": False,
				"error": "Unsupported method",
				"supported": ["GET", "POST"],
				"method": method,
			}

		content_type = (resp.headers.get("content-type") or "").lower()
		if "application/json" in content_type:
			body = resp.json()
		else:
			body = resp.text

		return {
			"ok": True,
			"method": method,
			"url": url,
			"status_code": resp.status_code,
			"headers": dict(resp.headers),
			"body": body,
		}
	except Exception as e:
		return {
			"ok": False,
			"method": method,
			"url": url,
			"error": str(e),
		}
```

Input schema:

```json
{
  "type": "object",
  "properties": {
	"url": { "type": "string" },
	"method": { "type": "string", "enum": ["GET", "POST"] },
	"timeout": { "type": "number" },
	"headers": { "type": "object" },
	"params": { "type": "object" },
	"json": { "type": "object" }
  },
  "required": ["url"]
}
```

## 8. Agent Invocation Example / Agent 调用示例

```python
def run(input_text, context):
	text = input_text.strip().lower()

	if text in ["测接口", "test api"]:
		return call_tool("http_fetch", {
			"url": "http://127.0.0.1:8000/health",
			"method": "GET",
			"timeout": 5
		})

	if "加" in text:
		return call_tool("calculate", {
			"operation": "add",
			"a": 22,
			"b": 3
		})

	return {"use_llm": True}
```

## 9. Troubleshooting / 常见问题

1. 看不到新 Tool
原因：创建在其他 project，或 `Shared In Project=false`。

2. Agent 不调用 Tool
原因：Agent 不是 `run_mode=code`，或未在 `Associate Tools` 关联。

3. 报 `Import not allowed`
原因：导入了白名单外模块。

4. 报 `name 'xxx' is not defined`
原因：沙箱白名单未放行对应内置函数，需在后端扩展白名单。
