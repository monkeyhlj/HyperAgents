from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import re
import uuid

import httpx
from openai import OpenAI

from app.core.config import settings


@dataclass
class ProviderGenerationRequest:
    text: str
    model_name: str
    system_prompt: str | None = None
    # If provided, used as the full conversation history (overrides text/system_prompt).
    messages: list[dict] | None = None
    # OpenAI-format tool definitions for function calling.
    tools: list[dict] | None = None


@dataclass
class ProviderGenerationResponse:
    text: str
    # List of {id, name, arguments} dicts when the model requests tool calls.
    tool_calls: list[dict] | None = None


class ProviderClient:
    def generate(self, request: ProviderGenerationRequest) -> ProviderGenerationResponse:
        raise NotImplementedError


def _normalize_env_prefix(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
    return normalized.upper()


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    return value


def _supports_function_calling(model_name: str) -> bool:
    """Check if a model supports OpenAI-style function calling."""
    model = (model_name or "").lower().strip()
    
    # Models that support function calling
    supported_patterns = [
        "gpt-4",  # All GPT-4 variants (gpt-4o, gpt-4-turbo, etc.)
        "gpt-3.5-turbo-1106",  # Only 1106+ versions
        "claude-3",  # Anthropic Claude 3+
    ]
    
    # Models that explicitly don't support it
    unsupported_patterns = [
        "glm-",  # Zhipu GLM models (glm-4 might support, but glm-3.5/glm-5.1 don't)
        "qwen",  # Alibaba Qwen
        "ernie",  # Baidu ERNIE
        "text-davinci-002",
        "text-davinci-003",
    ]
    
    # Check unsupported first (more specific)
    for pattern in unsupported_patterns:
        if pattern in model:
            return False
    
    # Check supported patterns
    for pattern in supported_patterns:
        if pattern in model:
            return True
    
    # Default: assume doesn't support (safe fallback)
    return False


class OpenAIProviderClient(ProviderClient):
    def __init__(self, profile_name: str = "openai") -> None:
        self._profile_name = profile_name
        self._env_prefix = _normalize_env_prefix(profile_name)
        self._api_key = _env(f"{self._env_prefix}_API_KEY", settings.openai_api_key)
        self._base_url = _env(f"{self._env_prefix}_BASE_URL", settings.openai_base_url)
        self._default_model = _env(f"{self._env_prefix}_DEFAULT_MODEL", settings.openai_default_model)
        # Keep timeout aligned with local provider timeout to avoid hanging requests.
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=float(settings.model_request_timeout_seconds),
        )

    def generate(self, request: ProviderGenerationRequest) -> ProviderGenerationResponse:
        if not self._api_key and not self._base_url:
            raise RuntimeError(f"{self._env_prefix}_API_KEY is not configured")

        messages: list[dict] = request.messages or []
        if not messages:
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.text})

        kwargs: dict = {"model": request.model_name, "messages": messages, "temperature": 0.2}
        if request.tools:
            kwargs["tools"] = request.tools
            kwargs["tool_choice"] = "auto"

        result = self._client.chat.completions.create(**kwargs)
        choice = result.choices[0]
        msg = choice.message

        tool_calls: list[dict] | None = None
        if msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, AttributeError):
                    args = {}
                tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})

        return ProviderGenerationResponse(text=msg.content or "", tool_calls=tool_calls)


class LocalhostProviderClient(ProviderClient):
    def __init__(self) -> None:
        self._base_url = settings.localhost_llm_base_url.rstrip("/")

    def generate(self, request: ProviderGenerationRequest) -> ProviderGenerationResponse:
        messages: list[dict] = request.messages or []
        if not messages:
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.text})

        payload: dict = {"model": request.model_name, "messages": messages, "temperature": 0.2}
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = "auto"

        with httpx.Client(timeout=float(settings.model_request_timeout_seconds)) as client:
            response = client.post(f"{self._base_url}/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        msg = choice["message"]

        tool_calls: list[dict] | None = None
        if msg.get("tool_calls"):
            tool_calls = []
            for tc in msg["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"])
                except (json.JSONDecodeError, KeyError):
                    args = {}
                tool_calls.append({
                    "id": tc.get("id") or str(uuid.uuid4()),
                    "name": tc["function"]["name"],
                    "arguments": args,
                })

        return ProviderGenerationResponse(text=msg.get("content") or "", tool_calls=tool_calls)


class ProviderFactory:
    def get_client(self, provider_name: str, provider_profile: str | None = None) -> ProviderClient:
        normalized = provider_name.strip().lower()
        if normalized == "openai":
            return OpenAIProviderClient(profile_name=provider_profile or "openai")
        if normalized in {"localhost", "ollama", "vllm"}:
            return LocalhostProviderClient()
        return OpenAIProviderClient(profile_name=provider_profile or provider_name)


provider_factory = ProviderFactory()
