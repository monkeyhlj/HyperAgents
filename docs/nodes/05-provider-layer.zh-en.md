# Node 05: Provider Layer (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## LLM Provider / Embedding Provider

中文：
Provider 层把上游模型能力统一成标准接口，当前支持：
- OpenAI
- localhost (兼容 OpenAI-style API，例如 Ollama/vLLM 网关)

English:
The provider layer standardizes upstream model capabilities. Current providers:
- OpenAI
- localhost (OpenAI-style API gateway, e.g., Ollama/vLLM)

## 配置项 / Configuration

中文：
所有配置统一从工作区根目录 `.env` 读取（模板见 `.env.example`）。

English:
All configuration is read from workspace-root `.env` (template: `.env.example`).

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_DEFAULT_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `LOCALHOST_LLM_BASE_URL`
- `LOCALHOST_DEFAULT_MODEL`
- `LOCALHOST_EMBEDDING_MODEL`
- `RUNTIME_DEFAULT_PROVIDER`
- `EMBEDDING_PROVIDER`
- `MODEL_REQUEST_TIMEOUT_SECONDS`

### provider_profile 规则 / provider_profile Convention

中文：
- 默认模板或资源可以带 `provider_profile`，用于映射环境变量前缀。
- 例如 `provider_profile=zhipu` 时，后端读取 `ZHIPU_API_KEY`、`ZHIPU_BASE_URL`、`ZHIPU_DEFAULT_MODEL`。
- `model_provider` 只表示运行时客户端类型，不存放真实密钥。

English:
- Default templates or resources can carry `provider_profile` to map env-variable prefixes.
- For example, `provider_profile=zhipu` makes the backend read `ZHIPU_API_KEY`, `ZHIPU_BASE_URL`, and `ZHIPU_DEFAULT_MODEL`.
- `model_provider` only indicates the runtime client type; it does not store secrets.

### 默认模板文件 / Default Template File

中文：
- 默认模板文件位于 `backend/app/core/default_resources.json`。
- 这里适合放“可展示、可选择”的默认 Agent 模板，不适合放真实 API Key。

English:
- The default template file is `backend/app/core/default_resources.json`.
- It is suitable for displayable/selectable Agent templates, not for real API keys.

## 执行路径 / Execution Flow

中文：
1. Chat API 收到消息
2. 若提供 `agent_id`，读取 agent resource 的 provider/model/prompt
3. Runtime 调用 LLM Provider 生成回复
4. Memory 写入时调用 Embedding Provider 生成向量

English:
1. Chat API receives message
2. If `agent_id` exists, read provider/model/prompt from agent resource
3. Runtime calls LLM provider to generate response
4. Memory write calls embedding provider to generate vectors

## 代码位置 / Code References

- `backend/app/runtime/providers.py`
- `backend/app/runtime/embeddings.py`
- `backend/app/runtime/executor.py`
- `backend/app/core/config.py`
