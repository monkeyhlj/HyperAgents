from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re

from app.core.config import settings
from app.runtime.provider_connections import ProviderConnectionCredentials, test_openai_compatible_chat
from app.runtime.providers import ProviderGenerationRequest, provider_factory


@dataclass
class LLMRequest:
    text: str
    model_provider: str | None = None
    model_name: str | None = None
    provider_profile: str | None = None
    provider_connection_id: str | None = None
    provider_connection: dict | None = None
    system_prompt: str | None = None
    # Full conversation history (overrides text/system_prompt when provided).
    messages: list[dict] | None = None
    # OpenAI-format tool definitions for function calling.
    tools: list[dict] | None = None
    # Optional output cap to keep long-running design calls from timing out.
    max_tokens: int | None = None


@dataclass
class LLMResponse:
    text: str
    provider: str
    model_name: str
    ok: bool = True
    used_fallback: bool = False
    error: str | None = None
    # Populated when the model requests tool calls instead of (or alongside) text.
    tool_calls: list[dict] | None = None


class LLMService:
    """Unified model gateway used by API and runtime orchestration layers."""

    def generate(self, request: LLMRequest) -> LLMResponse:
        provider_name = request.model_provider or settings.runtime_default_provider
        resolved_model = request.model_name or self._default_model(
            provider_name,
            request.provider_profile,
            request.provider_connection,
        )

        try:
            if request.provider_connection:
                connection = request.provider_connection
                from openai import OpenAI as _OpenAI
                from app.runtime.provider_connections import normalize_base_url
                _oa_client = _OpenAI(
                    api_key=str(connection.get("api_key") or "not-needed"),
                    base_url=normalize_base_url(str(connection.get("base_url") or "")),
                    timeout=float(settings.model_request_timeout_seconds),
                )
                _messages: list[dict] = request.messages or []
                if not _messages:
                    if request.system_prompt:
                        _messages = [{"role": "system", "content": request.system_prompt}]
                    _messages = [*_messages, {"role": "user", "content": request.text}]
                _kwargs: dict = {"model": resolved_model, "messages": _messages, "temperature": 0.2}
                if request.max_tokens is not None:
                    _kwargs["max_tokens"] = request.max_tokens
                if request.tools:
                    _kwargs["tools"] = request.tools
                    _kwargs["tool_choice"] = "auto"
                _result = _oa_client.chat.completions.create(**_kwargs)
                _choice = _result.choices[0]
                _msg = _choice.message
                _tool_calls: list[dict] | None = None
                if _msg.tool_calls:
                    import json as _json
                    _tool_calls = []
                    for _tc in _msg.tool_calls:
                        try:
                            _args = _json.loads(_tc.function.arguments)
                        except Exception:
                            _args = {}
                        _tool_calls.append({"id": _tc.id, "name": _tc.function.name, "arguments": _args})
                return LLMResponse(
                    text=_msg.content or "",
                    provider="provider_connection",
                    model_name=resolved_model,
                    tool_calls=_tool_calls,
                )

            client = provider_factory.get_client(provider_name, provider_profile=request.provider_profile)
            gen_response = client.generate(
                ProviderGenerationRequest(
                    text=request.text,
                    model_name=resolved_model,
                    system_prompt=request.system_prompt,
                    messages=request.messages,
                    tools=request.tools,
                    max_tokens=request.max_tokens,
                )
            )
            return LLMResponse(
                text=gen_response.text,
                provider=provider_name,
                model_name=resolved_model,
                tool_calls=gen_response.tool_calls,
            )
        except Exception as exc:
            # Keep backward-compatible fallback text behavior for callers.
            fallback = f"[runtime-fallback:{provider_name}] {request.text} | error={exc}"
            return LLMResponse(
                text=fallback,
                provider=provider_name,
                model_name=resolved_model,
                ok=False,
                used_fallback=True,
                error=str(exc),
            )

    @staticmethod
    def code_requests_llm(result_text: str) -> bool:
        """Return True when code-mode output explicitly asks for LLM fallback.

        Expected code output shape:
        {"use_llm": true}
        """
        try:
            payload = json.loads(result_text)
        except Exception:
            return False
        return isinstance(payload, dict) and bool(payload.get("use_llm"))

    def _default_model(
        self,
        provider_name: str,
        provider_profile: str | None = None,
        provider_connection: dict | None = None,
    ) -> str:
        if provider_connection and provider_connection.get("default_model"):
            return str(provider_connection["default_model"])
        
        if provider_profile:
            # Normalize profile name to env var prefix (e.g., "custom-nvidia" -> "CUSTOM_NVIDIA")
            profile_name = re.sub(r"[^A-Za-z0-9]+", "_", provider_profile.strip()).strip("_").upper()
            env_value = os.getenv(f"{profile_name}_DEFAULT_MODEL")
            if env_value:
                return env_value
            
            # Backward compatibility for NVIDIA/NVIDA spellings
            if provider_profile.lower() in {"nvidia", "nvida"}:
                env_value = os.getenv("NVIDA_DEFAULT_MODEL") or os.getenv("NVIDIA_DEFAULT_MODEL")
                if env_value:
                    return env_value
                return "z-ai/glm-5.2"
        
        # Provider-level fallback
        if provider_name.strip().lower() == "openai":
            return settings.openai_default_model
        if provider_name.strip().lower() in {"nvidia", "nvida"}:
            # NVIDIA fallback
            env_value = os.getenv("NVIDA_DEFAULT_MODEL") or os.getenv("NVIDIA_DEFAULT_MODEL")
            return env_value or "z-ai/glm-5.2"
        
        # Default to localhost
        return settings.localhost_default_model


llm_service = LLMService()
