from __future__ import annotations

from dataclasses import dataclass

import httpx
from openai import OpenAI

from app.core.config import settings


@dataclass
class ProviderConnectionCredentials:
    provider_type: str
    base_url: str
    api_key: str


def normalize_base_url(value: str) -> str:
    return value.strip().rstrip("/")


def list_openai_compatible_models(credentials: ProviderConnectionCredentials) -> list[str]:
    base_url = normalize_base_url(credentials.base_url)
    headers = {}
    if credentials.api_key:
        headers["Authorization"] = f"Bearer {credentials.api_key}"

    with httpx.Client(timeout=float(settings.model_request_timeout_seconds)) as client:
        response = client.get(f"{base_url}/models", headers=headers)
        response.raise_for_status()
        data = response.json()

    raw_models = data.get("data") if isinstance(data, dict) else data
    if not isinstance(raw_models, list):
        return []

    models: list[str] = []
    for item in raw_models:
        if isinstance(item, dict):
            model_id = item.get("id") or item.get("name")
        else:
            model_id = str(item)
        if model_id:
            models.append(str(model_id))
    return sorted(set(models))


def test_openai_compatible_chat(
    credentials: ProviderConnectionCredentials,
    model_name: str,
    text: str = "ping",
    system_prompt: str | None = None,
) -> str:
    client = OpenAI(
        api_key=credentials.api_key or "not-needed",
        base_url=normalize_base_url(credentials.base_url),
        timeout=float(settings.model_request_timeout_seconds),
    )
    result = client.chat.completions.create(
        model=model_name,
        messages=_build_messages(text, system_prompt),
        temperature=0.2,
    )
    return result.choices[0].message.content or ""

def _build_messages(text: str, system_prompt: str | None = None) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": text})
    return messages
