# Node 05: Provider Layer (中文 + English)

导航 / Navigation: [返回项目首页](../../README.md) | [文档首页](../README.md) | [中文 README](../../README.zh.md) | [English README](../../README.en.md)

## LLM Provider / Embedding Provider

Provider 层把上游模型能力统一成标准接口，当前支持：

- `openai`: OpenAI-compatible provider。
- `localhost`: 本地 OpenAI-style API，例如 Ollama/vLLM 网关。
- env-prefix provider profile: 通过 `provider_profile` 映射自定义前缀，如 `ZHIPU_*`、`QWEN_*`。
- Project-level Provider Connection: 通过 UI/API 保存 OpenAI-compatible Base URL + API Key。

## 配置项 / Configuration

`.env` 仍是平台级配置入口：

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
- `PROVIDER_CONNECTION_SECRET_KEY`

## provider_profile 规则 / provider_profile Convention

- 默认模板或资源可以带 `provider_profile`，用于映射环境变量前缀。
- 例如 `provider_profile=zhipu` 时，后端读取 `ZHIPU_API_KEY`、`ZHIPU_BASE_URL`、`ZHIPU_DEFAULT_MODEL`。
- `model_provider` 只表示运行时客户端类型，不存放真实密钥。

## Provider Connection / 项目级 Provider Connection

Provider Connection 适合用户在项目内通过 UI 配置模型连接：

- `base_url`: OpenAI-compatible endpoint。
- `api_key`: 写入时加密保存，返回时只展示 masked key。
- `default_model`: 默认模型。
- `model_list_cache`: `/models` 探测结果缓存。
- `last_test_status/error/at`: 最近一次测试结果。

对应 API：

- `POST /api/v1/provider-connections/projects/{project_id}/probe-models`
- `POST /api/v1/provider-connections/projects/{project_id}/test`
- `GET/POST /api/v1/provider-connections/projects/{project_id}`
- `GET/PATCH/DELETE /api/v1/provider-connections/{connection_id}`
- `POST /api/v1/provider-connections/{connection_id}/test`

## 执行路径 / Execution Flow

1. Chat API 收到消息。
2. 若提供 `agent_id`，读取 Agent resource 的 provider/model/prompt/config。
3. 若 Agent 绑定 `provider_connection_id`，优先使用项目级 Provider Connection。
4. 否则按 `provider_profile` / `.env` 配置解析 provider。
5. Runtime 调用 LLM Provider 生成回复。
6. Memory 写入时调用 Embedding Provider 生成向量。

## 代码位置 / Code References

- `backend/app/api/v1/provider_connections.py`
- `backend/app/runtime/provider_connections.py`
- `backend/app/runtime/providers.py`
- `backend/app/runtime/llm_service.py`
- `backend/app/runtime/embeddings.py`
- `backend/app/services/secret_box.py`
- `backend/app/core/config.py`
