from __future__ import annotations

from dataclasses import dataclass
import os
import re

import httpx
from openai import OpenAI

from app.core.config import settings


@dataclass
class ProviderGenerationRequest:
    text: str
    model_name: str
    system_prompt: str | None = None


class ProviderClient:
    def generate(self, request: ProviderGenerationRequest) -> str:
        raise NotImplementedError


def _normalize_env_prefix(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
    return normalized.upper()


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    return value


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

    def generate(self, request: ProviderGenerationRequest) -> str:
        if not self._api_key and not self._base_url:
            raise RuntimeError(f"{self._env_prefix}_API_KEY is not configured")

        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.text})

        result = self._client.chat.completions.create(
            model=request.model_name,
            messages=messages,
            temperature=0.2,
        )
        return result.choices[0].message.content or ""


class LocalhostProviderClient(ProviderClient):
    def __init__(self) -> None:
        self._base_url = settings.localhost_llm_base_url.rstrip("/")

    def generate(self, request: ProviderGenerationRequest) -> str:
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.text})

        payload = {
            "model": request.model_name,
            "messages": messages,
            "temperature": 0.2,
        }

        with httpx.Client(timeout=float(settings.model_request_timeout_seconds)) as client:
            response = client.post(f"{self._base_url}/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class ProviderFactory:
    def get_client(self, provider_name: str, provider_profile: str | None = None) -> ProviderClient:
        normalized = provider_name.strip().lower()
        if normalized == "openai":
            return OpenAIProviderClient(profile_name=provider_profile or "openai")
        if normalized in {"localhost", "ollama", "vllm"}:
            return LocalhostProviderClient()
        return OpenAIProviderClient(profile_name=provider_profile or provider_name)


provider_factory = ProviderFactory()
