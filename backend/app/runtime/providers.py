from __future__ import annotations

from dataclasses import dataclass

import httpx
from openai import OpenAI

from app.core.config import settings


@dataclass
class ChatGenerationRequest:
    text: str
    model_name: str
    system_prompt: str | None = None


class ProviderClient:
    def generate(self, request: ChatGenerationRequest) -> str:
        raise NotImplementedError


class OpenAIProviderClient(ProviderClient):
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def generate(self, request: ChatGenerationRequest) -> str:
        if not settings.openai_api_key and not settings.openai_base_url:
            raise RuntimeError("OPENAI_API_KEY is not configured")

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

    def generate(self, request: ChatGenerationRequest) -> str:
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
    def get_client(self, provider_name: str) -> ProviderClient:
        normalized = provider_name.strip().lower()
        if normalized == "openai":
            return OpenAIProviderClient()
        if normalized in {"localhost", "ollama", "vllm"}:
            return LocalhostProviderClient()
        raise ValueError(f"Unsupported model provider: {provider_name}")


provider_factory = ProviderFactory()
