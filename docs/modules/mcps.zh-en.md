# MCPs Module Guide / MCPs 模块说明

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [Tools Guide](./tools.zh-en.md)

## 1. Purpose / 作用

中文：
MCP 资源用于描述外部 MCP server 的连接方式，并被 Agent 在运行时按配置发现和调用。

English:
MCP resources describe how to connect to external MCP servers, so agents can discover and call remote capabilities.

## 1.1 当前支持状态 / Current Support Status

| 特性 / Feature | 状态 / Status | 说明 / Notes |
|---|---|---|
| **streamable_http** | ✅ **已支持** | HTTP/HTTPS 连接方式，可直接使用 |
| **stdio** | ⏳ 规划中 | 本地进程启动模式，暂不可用 |
| 工具调用 / Tool Calling | ✅ 已支持 | Agent code 模式可通过 call_mcp() 调用 MCP 工具 |
| 工具发现 / Tool Discovery | ✅ 已支持 | 可通过 list_mcps() 列举 MCP 和工具；probe API 可测试连接 |
| Headers/Auth | ✅ 已支持 | 支持 Bearer token / API key 等认证方式 |
| 工具缓存 / Tool Caching | ⏳ 规划中 | 工具列表缓存机制暂未实现 |

**建议：当前请使用 HTTP 方式部署 MCP server，或使用可 HTTP 暴露的兼容网关。**

## 2. MCP Config Shape / MCP 配置结构

### 核心字段说明 / Core Fields

推荐完整字段结构：

```json
{
	"transport": "streamable_http",
	"endpoint_url": "http://127.0.0.1:8099",
	"command": "",
	"args": [],
	"headers": {
		"Authorization": "Bearer your-token-here",
		"X-Custom-Header": "value"
	},
	"env": {
		"MCP_DEBUG": "true",
		"MCP_LOG_LEVEL": "debug"
	},
	"timeout_seconds": 8
}
```

#### 字段详解 / Field Details

1. **transport** (必填)
   - 当前值：`streamable_http`（仅支持此值）
   - 说明：MCP 连接方式。当前 **仅支持 HTTP 方式**；stdio 支持在规划中，暂不可用。

2. **endpoint_url** (当 transport=streamable_http 时必填)
   - 示例：`http://127.0.0.1:8099` 或 `https://api.example.com/mcp`
   - 说明：MCP server 的 HTTP 基础地址。系统会自动拼接 `/health` 和 `/tools/call` 接口。

3. **command** (当 transport=stdio 时需要；当前不用填)
   - 说明：stdio 模式启动命令，如 `python`。**暂不支持，文档占位。**

4. **args** (当 transport=stdio 时需要；当前不用填)
   - 示例：`["scripts/my_mcp_server.py"]`
   - 说明：stdio 模式命令行参数数组。**暂不支持，文档占位。**

5. **headers** (可选)
   - 作用：HTTP 请求头，用于认证和自定义字段
   - 使用场景：
     - Bearer token 认证：`"Authorization": "Bearer xxx"`
     - API key 认证：`"X-API-Key": "xxx"`
     - 自定义业务头：`"X-Request-ID": "123"`
   - 注意：
     - 在"Create/Edit MCP"页面，点击 `Headers JSON` 编辑器输入
     - 支持 JSON 对象格式：`{"key1": "value1", "key2": "value2"}`
     - 留空表示不添加额外请求头
   - 示例：
     ```json
     {
       "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
       "X-Client-ID": "hyperagents-v1"
     }
     ```

6. **env** (可选)
   - 作用：环境变量，传递给 MCP server 进程（**当前 HTTP 模式下实际不生效，仅供文档一致性**）
   - 使用场景：
     - 调试标记：`"DEBUG": "true"`
     - 日志级别：`"LOG_LEVEL": "debug"`
     - MCP 特定配置：`"MCP_FEATURE_FLAG": "enable_dynamic_tools"`
   - 注意：
     - 当前 HTTP 模式下，env 字段被记录但不被传输到 MCP server
     - 主要用途是文档和未来 stdio 模式的兼容性预留
   - 示例：
     ```json
     {
       "DEBUG": "false",
       "LOG_LEVEL": "info"
     }
     ```

7. **timeout_seconds** (可选，默认=8)
   - 范围：1-300 秒
   - 作用：HTTP 请求超时时间，包括健康检查和工具调用
   - 说明：
     - 若 MCP server 响应耗时较长，增大此值（如 30s）
     - 若网络延迟高，建议 10-15s
     - 过小会导致超时错误，过大会拖累前端响应

### Advanced Config JSON / 高级配置 JSON

在"Create/Edit MCP"页面最下方，还有一个 `Advanced MCP Config JSON (Editable)` 编辑器。

作用：存放 MCP-specific 的扩展配置，不被核心字段覆盖。

示例用途：

```json
{
  "feature_flags": {
    "allow_dynamic_tools": true,
    "enable_tool_caching": false
  },
  "metadata": {
    "owner": "platform-team",
    "version": "1.0.0",
    "tags": ["production", "approved"]
  },
  "routing": {
    "primary_region": "us-east",
    "fallback_region": "us-west"
  },
  "retry_policy": {
    "max_attempts": 3,
    "backoff_seconds": 2
  }
}
```

使用建议：

- **feature_flags**：用于启用/禁用 MCP server 的可选特性
- **metadata**：用于记录 MCP 的来源、版本、所有者信息，方便审计和治理
- **routing**：用于多区域部署时的路由策略（当前实验性质）
- **retry_policy**：用于定义 MCP 调用的重试策略（当前实验性质）

注意：
- 高级配置不会影响核心 HTTP 连接，仅作为元数据或日志参考
- 前端表单提交时，会自动将核心字段（transport/endpoint_url/headers/env/timeout_seconds）与高级配置合并保存

## 3. Frontend Pages / 前端页面详解

### MCPs List

MCP 列表页面显示已创建的 MCP 资源及其状态：

1. **Transport 列**：显示连接方式（当前只显示 `streamable_http`）
2. **Endpoint/Command 列**：
   - HTTP 模式：显示 endpoint_url
   - stdio 模式：显示 command（暂不支持）
3. **Last Test 列**：
   - `untested` (灰色)：尚未测试或上次测试失败后清空
   - `ok` (绿色)：上次测试连接成功，工具列表可用
   - `failed` (红色)：上次测试连接失败
4. **Test 按钮**：点击后调用 probe API，验证当前配置是否可连接

### Create/Edit MCP - 表单说明 / Form Fields

#### 第一部分：基础配置

- **Project** (必填)：选择 MCP 资源所属项目
- **Name** (必填)：MCP 资源名称，用于 Agent 中 call_mcp() 引用，如 `testmcp`、`github-api`
- **Visibility** (必填)：
  - `private`：仅所有者可见
  - `project`：项目成员可见
  - `public`：公开可见
- **Description**：MCP 资源描述，用于文档和搜索

#### 第二部分：MCP 连接配置

##### Transport (必填)

- 选择 `streamable_http`（当前唯一选项）
- `stdio` 灰显，暂不支持

##### Endpoint URL (当 transport=streamable_http 时必填)

- **作用**：MCP server 的 HTTP 基础地址
- **示例**：
  - 本地：`http://127.0.0.1:8099`
  - 远程：`https://mcp.company.com/api`
  - 自定义端口：`http://localhost:9000`
- **验证**：系统会自动拼接 `/health` 和 `/tools` 进行探测
- **常见错误**：
  - 末尾带 `/`：会被自动裁剪，无影响
  - 协议写错：确保是 `http://` 或 `https://`
  - 域名解析失败：检查网络连接和 DNS

##### Timeout (秒)

- **默认值**：8 秒
- **推荐范围**：5-30 秒
- **调整建议**：
  - 网络延迟 > 2s：设置为 15-20s
  - MCP server 初始化慢：设置为 30s
  - 本地测试：可设置 3-5s 快速反馈
- **过小风险**：健康检查或工具调用超时
- **过大风险**：前端对话等待时间长，影响用户体验

##### Quick Test 按钮

- **点击后**：自动调用 probe API 测试当前配置
- **结果**：
  - 成功：显示绿色，列出可用工具
  - 失败：显示红色，显示错误原因
- **场景**：
  - 新增 MCP 时快速验证配置正确性
  - 修改 endpoint/timeout 后验证连接
  - 保存前最后检查一遍

#### 第三部分：认证与扩展配置

##### Headers JSON (可选)

- **编辑器**：可视化 JSON 编辑器
- **作用**：添加 HTTP 请求头，用于认证和自定义参数
- **常见用途**：

```json
{
  "Authorization": "Bearer your-jwt-token-here",
  "X-API-Key": "sk-1234567890",
  "User-Agent": "HyperAgents/1.0"
}
```

- **字段说明**：
  - `Authorization`：OAuth/Bearer token 或 Basic 认证
  - `X-API-Key` / `X-Secret`：API key 认证
  - 自定义头：任何业务需要的 HTTP 头
- **注意**：
  - 留空表示不添加任何请求头
  - 敏感信息（token/key）请妥善管理，不要提交到公开仓库
  - 系统会自动添加 `Content-Type: application/json`

##### Env JSON (可选)

- **编辑器**：可视化 JSON 编辑器
- **作用**：记录环境变量和 MCP 特定配置（**HTTP 模式下当前不传输，仅文档用途**）
- **常见用途**：

```json
{
  "DEBUG": "false",
  "LOG_LEVEL": "info",
  "MCP_FEATURE_FLAG_DYNAMIC_TOOLS": "true"
}
```

- **字段说明**：
  - `DEBUG`：调试开关，true/false
  - `LOG_LEVEL`：日志级别，debug/info/warn/error
  - `MCP_*` 前缀：MCP server 特定配置
- **当前限制**：
  - HTTP 模式下，env 变量不会实际传送到 MCP server
  - 仅用于配置文档和元数据存储
  - 未来 stdio 模式会真正使用
- **建议**：如需 MCP server 动态配置，优先通过 Headers 中的自定义字段或 endpoint URL 的查询参数传递

##### Advanced MCP Config JSON (可选)

- **编辑器**：代码编辑器，支持完整 JSON 格式
- **作用**：存放 MCP-specific 的扩展配置，不被核心字段覆盖
- **常见用途**：

```json
{
  "feature_flags": {
    "allow_dynamic_tools": true,
    "enable_caching": false,
    "strict_schema_validation": true
  },
  "metadata": {
    "owner": "platform-team",
    "version": "v1.2.0",
    "tags": ["production", "critical"],
    "on_call": "team-slack-channel"
  },
  "routing": {
    "primary_endpoint": "http://mcp-primary:8000",
    "fallback_endpoint": "http://mcp-fallback:8000",
    "lb_strategy": "round-robin"
  },
  "retry": {
    "max_attempts": 3,
    "initial_backoff_ms": 100,
    "max_backoff_ms": 5000
  }
}
```

- **字段建议**：
  - `feature_flags`：MCP server 的可选特性开关
  - `metadata`：记录来源、版本、所有者、on-call 联系方式等
  - `routing`：多副本部署时的路由策略（实验性）
  - `retry`：MCP 调用的重试策略（实验性）
- **注意**：
  - **格式必须是有效 JSON**，否则保存时会报错
  - 高级配置与核心字段自动合并，合并后完整 config 被保存到资源中
  - 修改高级配置不会影响 HTTP 连接，仅用于元数据和业务逻辑参考

#### 第四部分：保存与验证

- **Cancel** 按钮：放弃修改，返回 MCPs 列表
- **Create/Save Changes** 按钮：保存 MCP 资源
- **验证流程**：
  1. 检查基础字段完整性（Project/Name/Transport/Endpoint）
  2. 验证 Headers JSON 和 Env JSON 格式
  3. 验证高级配置 JSON 格式
  4. 自动合并所有字段到最终 config
  5. 保存到数据库

#### 使用工作流示例 / Example Workflow

**场景：创建一个需要 Bearer token 认证的远程 MCP**

1. 进入 Resources -> MCPs -> Create MCP
2. **Project**：选择 `my-project`
3. **Name**：输入 `github-mcp`
4. **Visibility**：选择 `project`
5. **Description**：输入 `GitHub API integration`
6. **Transport**：选择 `streamable_http`
7. **Endpoint URL**：输入 `https://github-mcp.company.com`
8. **Timeout**：设置 `10`
9. **Headers JSON**：
   ```json
   {
     "Authorization": "Bearer ghp_xxxxxxxxxxxx",
     "X-Request-ID": "github-integration"
   }
   ```
10. **Env JSON**：留空或填入 `{}`
11. **Advanced Config**：
    ```json
    {
      "metadata": {
        "owner": "devops-team",
        "version": "v1.0.0",
        "tags": ["github", "external-api"]
      }
    }
    ```
12. 点击 **Test MCP Connection** 验证连接
13. 点击 **Create** 保存

#### 添加其他官方服务 MCP（推荐流程）/ Add Other Official Service MCPs

如果你要接入 GitHub、Notion、Slack、Atlassian 等官方服务 MCP，建议按下面步骤：

1. 先确认该服务提供的是 **HTTP MCP endpoint**（当前系统只支持 `streamable_http`）
2. 确认认证方式（Bearer Token / API Key / 自定义 Header）
3. 在 Create MCP 中填写 endpoint 与 headers
4. 先点 `Test MCP Connection`，看到 tools 列表后再保存
5. 在 Agent 中通过 `call_mcp("mcp-name", "tool-name", {...})` 调用

官方服务接入最关键是 `Headers JSON`。下面给出可直接改值的模板。

##### 模板 1：Bearer Token（最常见）

适用于 OAuth2 或 Personal Access Token。

```json
{
  "transport": "streamable_http",
  "endpoint_url": "https://<official-mcp-endpoint>",
  "headers": {
    "Authorization": "Bearer <YOUR_TOKEN>",
    "User-Agent": "HyperAgents/1.0"
  },
  "env": {},
  "timeout_seconds": 12
}
```

##### 模板 2：API Key Header

适用于要求 `X-API-Key` 或类似头的服务。

```json
{
  "transport": "streamable_http",
  "endpoint_url": "https://<official-mcp-endpoint>",
  "headers": {
    "X-API-Key": "<YOUR_API_KEY>",
    "X-Client-ID": "hyperagents"
  },
  "env": {},
  "timeout_seconds": 12
}
```

##### 模板 3：带版本头/租户头

适用于需要额外版本与租户标识的服务。

```json
{
  "transport": "streamable_http",
  "endpoint_url": "https://<official-mcp-endpoint>",
  "headers": {
    "Authorization": "Bearer <YOUR_TOKEN>",
    "X-Tenant-ID": "<TENANT_ID>",
    "X-API-Version": "2026-01-01"
  },
  "env": {},
  "timeout_seconds": 15
}
```

##### 字段落位到页面时怎么填

- `Transport`: 选 `streamable_http`
- `Endpoint URL`: 填官方 MCP 地址（不要填普通 REST API 地址）
- `Headers JSON`: 粘贴上面模板里的 headers，并替换 token/key
- `Env JSON`: HTTP 模式可留 `{}`（当前仅记录，不传输）
- `Advanced MCP Config JSON`: 可选填 metadata，如 owner、version、tags

##### 官方服务接入常见错误

1. 把官方 REST API 地址当作 MCP endpoint
2. 漏掉 `Authorization` 或 token 过期
3. endpoint 可访问，但 `/tools` 返回为空（说明服务端未启用 MCP 工具）
4. 网络可达但超时，`timeout_seconds` 太小

##### 安全建议

1. token/key 不要写入仓库文档和截图
2. 建议使用最小权限 token，只开放需要的 scope
3. 定期轮换 token
4. 生产环境与测试环境使用不同 MCP 资源

## 4. Probe API / 连接测试接口

Endpoint:

- `POST /api/v1/registry/mcp/probe`

Request:

```json
{
	"project_id": "<project-id>",
	"config": {
		"transport": "streamable_http",
		"endpoint_url": "http://127.0.0.1:8099",
		"timeout_seconds": 8
	}
}
```

Response:

```json
{
	"ok": true,
	"transport": "streamable_http",
	"endpoint_url": "http://127.0.0.1:8099",
	"health_ok": true,
	"tools_ok": true,
	"tools": ["ping", "echo"],
	"error": null
}
```

当前限制：

1. probe 当前只支持 `streamable_http`
2. stdio probe 会返回明确提示（暂不支持）

## 5. Fake MCP Server for Testing / 本地假 MCP Server

项目内置了 mock server：

- [backend/scripts/mock_mcp_server.py](../../backend/scripts/mock_mcp_server.py)

启动命令：

```powershell
cd backend
.venv\Scripts\python.exe scripts\mock_mcp_server.py
```

默认地址：

- `http://127.0.0.1:8099`

可用接口：

1. `GET /health`
2. `GET /tools`
3. `POST /tools/call`

## 6. Suggested Test Flow / 建议测试流程

### 完整测试流程（5 步）

**第一步：启动后端 API**

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

验证：浏览器访问 `http://localhost:8000/docs`，看到 FastAPI Swagger UI

**第二步：启动 Fake MCP Server**

在另一个终端：

```powershell
cd backend
.venv\Scripts\python.exe scripts\mock_mcp_server.py
```

输出应该显示：`Uvicorn running on http://127.0.0.1:8099/`

**第三步：在 Resources -> MCPs -> Create MCP 填写配置**

1. **Project**：选择任意项目
2. **Name**：输入 `testmcp`
3. **Transport**：选择 `streamable_http`
4. **Endpoint URL**：输入 `http://127.0.0.1:8099`
5. **Timeout**：保持默认 `8` 秒
6. **Headers JSON**：留空或 `{}`
7. **Env JSON**：留空或 `{}`
8. 点击 **Quick Test** 验证连接，应该看到绿色提示和工具列表

**第四步：保存 MCP 资源**

点击 **Create**，返回 MCPs 列表，确认 `testmcp` 出现且 Last Test 显示 `ok`

**第五步：创建 Agent 并测试**

1. 进入 **Resources -> Agents -> Create Agent**
2. **Name**：输入 `test-agent`
3. **Custom Code** 模式，粘贴以下代码：

```python
def run(input_text, context):
    text = input_text.strip().lower()

    if text == "show mcp":
        # 显示 MCP 绑定信息
        return {
            "available_mcps": list_mcps(),
            "mcp_ids": context.get("config", {}).get("mcp_ids", [])
        }

    if text == "test mcp":
        # 调用 MCP 工具
        result = call_mcp("testmcp", "ping", {"message": "hello from agent"})
        return {"mcp_response": result}

    return {"use_llm": True}
```

4. **Associate MCPs**：选择 `testmcp`
5. 点击 **Create**

6. 进入 **Chat -> Workbench**
7. 在对话输入框输入：
   - `show mcp` → 应该返回 `available_mcps: ["testmcp"]` 和 Agent 的 mcp_ids
   - `test mcp` → 应该返回 MCP ping 工具的响应
   - 查看对话中的标签是否显示 `mcp: testmcp / tool: ping`

### 验收标准

所有测试通过表示 MCP 功能完整可用：

- ✅ MCP 资源创建成功
- ✅ Test MCP Connection 返回绿色且工具列表非空
- ✅ Agent 可关联多个 MCP
- ✅ Agent custom code 可调用 call_mcp() 和 list_mcps()
- ✅ 对话响应包含 used_mcps 标签
- ✅ 前端 Workbench 显示 MCP 调用记录

## 8. Using MCPs in Agent / 在 Agent 中使用 MCP

### 关联 MCP 到 Agent

在 **Resources -> Agents -> Create/Edit Agent** 页面：

1. **Associate MCPs** 下拉框：选择要关联的 MCP（多选）
2. 示例：关联 `testmcp` 和 `github-mcp`

### 在 Agent Custom Code 中调用 MCP

在 Agent 的 **Custom Code** 编辑器中（code mode），使用 sandbox 提供的函数：

```python
def run(input_text, context):
    text = input_text.strip().lower()

    # 列出可用的 MCP
    if text == "show mcps":
        return {
            "available_mcps": list_mcps(),
            "mcp_ids": context.get("config", {}).get("mcp_ids", [])
        }

    # 调用 MCP 工具
    if text.startswith("github "):
        query = text[7:]  # 去掉 "github " 前缀
        return call_mcp("github-mcp", "search_repos", {"q": query})

    # 调用另一个 MCP
    if text == "test ping":
        result = call_mcp("testmcp", "ping", {"message": "hello"})
        return {"mcp_result": result}

    # 无法处理，回退到 LLM
    return {"use_llm": True}
```

### MCP 调用 API 签名

#### call_mcp(mcp_name, tool_name, input_data)

**参数说明**：

- `mcp_name` (str)：MCP 资源名称，必须与 Associate MCPs 中的名称一致
- `tool_name` (str)：MCP 中的工具名称，通过 list_mcps() 或 probe API 可查看
- `input_data` (dict)：工具输入，格式由 MCP server 定义

**返回值**：

- 成功：返回 MCP 服务器的响应（通常是 dict）
- 失败：抛出异常，Agent 返回错误信息

**示例**：

```python
# 简单调用
result = call_mcp("testmcp", "ping", {})

# 带参数调用
result = call_mcp("github-mcp", "search_repos", {
    "q": "python framework",
    "sort": "stars",
    "order": "desc"
})

# 处理结果
if result.get("ok"):
    data = result.get("data", {})
    return f"Success: {data}"
else:
    return f"MCP call failed: {result.get('error')}"
```

#### list_mcps()

**返回值**：

- 返回当前 Agent 关联的所有 MCP 名称列表

**示例**：

```python
mcps = list_mcps()  # 返回 ["testmcp", "github-mcp"]
return {"available_mcps": mcps}
```

### 调用结果会自动追踪

当 Agent code 调用 MCP 后，对话响应会自动包含 `used_mcps` 字段：

```json
{
  "session_id": "...",
  "role": "assistant",
  "text": "MCP 调用结果：...",
  "run_id": "...",
  "used_tools": [],
  "used_mcps": [
    {"mcp": "github-mcp", "tool": "search_repos"},
    {"mcp": "testmcp", "tool": "ping"}
  ]
}
```

在前端 Workbench 的对话中，Assistant 消息上方会显示彩色标签：

- 橙色：`tool: xxx`（调用的 Tool）
- 蓝色：`mcp: xxx / tool: yyy`（调用的 MCP 工具）

### 常见问题 / FAQ

**Q1: 调用 MCP 时出现 "MCP not found" 错误**

A: 检查：
1. MCP 名称是否与 Associate MCPs 中的名称完全一致（区分大小写）
2. MCP 是否已保存并通过了 Test MCP Connection
3. Agent 配置是否已保存

**Q2: 调用 MCP 工具时出现 "Tool not found" 错误**

A: 检查：
1. 工具名称是否与 MCP server 的工具列表一致
2. 通过 list_mcps() 确认工具确实存在
3. 通过 probe API 再次测试 MCP 连接和工具列表

**Q3: MCP 调用超时**

A: 调整：
1. MCP 资源的 Timeout 设置（增大到 15-30 秒）
2. 检查网络连接和 MCP server 状态
3. 检查 Custom Code 逻辑是否正确处理超时异常

**Q4: Headers 中的 token 每次都要更新吗**

A: 目前是。建议：
1. 定期在 MCP 资源中更新 token
2. 如果 MCP server 支持长期 token，配置长期 token
3. 考虑使用环境变量或密钥管理服务（未来版本支持）
