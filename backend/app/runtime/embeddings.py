from __future__ import annotations

import json
from dataclasses import dataclass

import httpx
from openai import OpenAI

from app.core.config import settings


@dataclass
class EmbeddingRequest:
    text: str
    provider: str
    model: str


class EmbeddingProvider:
    def generate_embedding(self, request: EmbeddingRequest) -> list[float]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def generate_embedding(self, request: EmbeddingRequest) -> list[float]:
        if not settings.openai_api_key and not settings.openai_base_url:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        result = self._client.embeddings.create(model=request.model, input=request.text)
        return list(result.data[0].embedding)


class LocalhostEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._base_url = settings.localhost_llm_base_url.rstrip("/")

    def generate_embedding(self, request: EmbeddingRequest) -> list[float]:
        payload = {"model": request.model, "input": request.text}
        with httpx.Client(timeout=float(settings.model_request_timeout_seconds)) as client:
            response = client.post(f"{self._base_url}/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()
            return list(data["data"][0]["embedding"])


class EmbeddingFactory:
    def get_provider(self, provider_name: str) -> EmbeddingProvider:
        normalized = provider_name.strip().lower()
        if normalized == "openai":
            return OpenAIEmbeddingProvider()
        if normalized in {"localhost", "ollama", "vllm"}:
            return LocalhostEmbeddingProvider()
        raise ValueError(f"Unsupported embedding provider: {provider_name}")

    def resolve_model(self, provider_name: str, model: str | None) -> str:
        if model:
            return model
        normalized = provider_name.strip().lower()
        if normalized == "openai":
            return settings.openai_embedding_model
        return settings.localhost_embedding_model


def serialize_memory_content(content: dict) -> str:
    # Stable JSON string is used as embedding input when no custom text is supplied.
    return json.dumps(content, ensure_ascii=True, sort_keys=True)


embedding_factory = EmbeddingFactory()
