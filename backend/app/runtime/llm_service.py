from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re

from app.core.config import settings
from app.runtime.providers import ProviderGenerationRequest, provider_factory


@dataclass
class LLMRequest:
    text: str
    model_provider: str | None = None
    model_name: str | None = None
    provider_profile: str | None = None
    system_prompt: str | None = None


@dataclass
class LLMResponse:
    text: str
    provider: str
    model_name: str
    ok: bool = True
    used_fallback: bool = False
    error: str | None = None


class LLMService:
    """Unified model gateway used by API and runtime orchestration layers."""

    def generate(self, request: LLMRequest) -> LLMResponse:
        provider_name = request.model_provider or settings.runtime_default_provider
        resolved_model = request.model_name or self._default_model(provider_name, request.provider_profile)

        try:
            client = provider_factory.get_client(provider_name, provider_profile=request.provider_profile)
            text = client.generate(
                ProviderGenerationRequest(
                    text=request.text,
                    model_name=resolved_model,
                    system_prompt=request.system_prompt,
                )
            )
            return LLMResponse(text=text, provider=provider_name, model_name=resolved_model)
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

    def _default_model(self, provider_name: str, provider_profile: str | None = None) -> str:
        if provider_profile:
            profile_name = re.sub(r"[^A-Za-z0-9]+", "_", provider_profile.strip()).strip("_").upper()
            env_value = os.getenv(f"{profile_name}_DEFAULT_MODEL")
            if env_value:
                return env_value
        if provider_name.strip().lower() == "openai":
            return settings.openai_default_model
        return settings.localhost_default_model


llm_service = LLMService()
