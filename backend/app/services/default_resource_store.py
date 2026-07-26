import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.core.config import settings  # noqa: F401 - ensures workspace .env is loaded
from app.models.enums import ResourceKind, Visibility
from app.schemas.resource import Resource, ResourceTemplate


DEFAULT_RESOURCES_FILE = Path(__file__).resolve().parents[1] / "core" / "default_resources.json"


_ENV_PROVIDER_TEMPLATES: list[dict] = [
    {
        "template_id": "agent-openai-env-default",
        "kind": ResourceKind.AGENT.value,
        "name": "OpenAI Assistant",
        "description": "OpenAI-compatible assistant template discovered from env.",
        "visibility": Visibility.PROJECT.value,
        "model_provider": "openai",
        "provider_profile": "openai",
        "env_prefix": "OPENAI",
        "default_model": "gpt-4o-mini",
        "config": {"system_prompt": "You are a helpful AI assistant."},
    },
    {
        "template_id": "agent-zhipu-env-default",
        "kind": ResourceKind.AGENT.value,
        "name": "Zhipu Assistant",
        "description": "Zhipu-compatible assistant template discovered from env.",
        "visibility": Visibility.PROJECT.value,
        "model_provider": "zhipu",
        "provider_profile": "zhipu",
        "env_prefix": "ZHIPU",
        "default_model": "glm-5.1",
        "config": {"system_prompt": "You are a helpful AI assistant."},
    },
    {
        "template_id": "agent-nvidia-env-default",
        "kind": ResourceKind.AGENT.value,
        "name": "NVIDIA Assistant",
        "description": "NVIDIA-compatible assistant template discovered from env.",
        "visibility": Visibility.PROJECT.value,
        "model_provider": "nvidia",
        "provider_profile": "nvidia",
        "env_prefix": "NVIDIA",
        "default_model": "z-ai/glm-5.2",
        "config": {"system_prompt": "You are a helpful AI assistant.", "engine_type": "react", "max_iterations": 10},
    },
    {
        "template_id": "agent-deepseek-env-default",
        "kind": ResourceKind.AGENT.value,
        "name": "DeepSeek Assistant",
        "description": "DeepSeek-compatible assistant template discovered from env.",
        "visibility": Visibility.PROJECT.value,
        "model_provider": "deepseek",
        "provider_profile": "deepseek",
        "env_prefix": "DEEPSEEK",
        "default_model": "deepseek-chat",
        "config": {"system_prompt": "You are a helpful AI assistant."},
    },
]


def _env_template_available(template: dict) -> bool:
    prefix = str(template.get("env_prefix") or "").strip().upper()
    if not prefix:
        return False
    if os.getenv(f"{prefix}_DEFAULT_MODEL"):
        return True
    if prefix in {"NVIDIA", "NVIDA"} and (os.getenv("NVIDIA_DEFAULT_MODEL") or os.getenv("NVIDA_DEFAULT_MODEL")):
        return True
    return False


def _env_template_to_resource(template: dict) -> ResourceTemplate:
    return ResourceTemplate(
        template_id=str(template["template_id"]),
        kind=ResourceKind(template["kind"]),
        name=str(template["name"]),
        description=str(template.get("description", "")),
        visibility=Visibility(template.get("visibility", Visibility.PROJECT.value)),
        model_provider=template.get("model_provider"),
        model_name=os.getenv(f"{template['env_prefix']}_DEFAULT_MODEL", template.get("default_model")),
        provider_profile=template.get("provider_profile"),
        config=dict(template.get("config") or {}),
    )


class DefaultResourceStore:
    def list_templates(self) -> list[ResourceTemplate]:
        templates_by_key: dict[tuple[str, str], ResourceTemplate] = {}
        if not DEFAULT_RESOURCES_FILE.exists():
            raw = []
        else:
            raw = json.loads(DEFAULT_RESOURCES_FILE.read_text(encoding="utf-8"))

        for item in raw:
            try:
                template = ResourceTemplate(
                    template_id=str(item["template_id"]),
                    kind=ResourceKind(item["kind"]),
                    name=str(item["name"]),
                    description=str(item.get("description", "")),
                    visibility=Visibility(item.get("visibility", Visibility.PROJECT.value)),
                    model_provider=item.get("model_provider"),
                    model_name=item.get("model_name"),
                    provider_profile=item.get("provider_profile"),
                    config=item.get("config") or {},
                )
                key = (template.kind.value, (template.provider_profile or template.model_provider or template.name).lower())
                templates_by_key[key] = template
            except Exception:
                continue

        for item in _ENV_PROVIDER_TEMPLATES:
            if not _env_template_available(item):
                continue
            template = _env_template_to_resource(item)
            key = (template.kind.value, (template.provider_profile or template.model_provider or template.name).lower())
            templates_by_key[key] = template

        return list(templates_by_key.values())

    def list_resources_for_project(
        self,
        project_id: str,
        kind: ResourceKind | None = None,
        visibility: Visibility | None = None,
    ) -> list[Resource]:
        templates = self.list_templates()
        result: list[Resource] = []
        for item in templates:
            if kind and item.kind != kind:
                continue
            if visibility and item.visibility != visibility:
                continue
            result.append(
                Resource(
                    id=str(uuid5(NAMESPACE_URL, f"default-resource:{item.template_id}")),
                    project_id=project_id,
                    owner_id="system",
                    kind=item.kind,
                    name=item.name,
                    description=item.description,
                    visibility=item.visibility,
                    model_provider=item.model_provider,
                    model_name=item.model_name,
                    provider_profile=item.provider_profile,
                    config=item.config,
                    source="default",
                    template_id=item.template_id,
                )
            )
        return result


default_resource_store = DefaultResourceStore()