import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.models.enums import ResourceKind, Visibility
from app.schemas.resource import Resource, ResourceTemplate


DEFAULT_RESOURCES_FILE = Path(__file__).resolve().parents[1] / "core" / "default_resources.json"


class DefaultResourceStore:
    def list_templates(self) -> list[ResourceTemplate]:
        if not DEFAULT_RESOURCES_FILE.exists():
            return []

        raw = json.loads(DEFAULT_RESOURCES_FILE.read_text(encoding="utf-8"))
        templates: list[ResourceTemplate] = []
        for item in raw:
            try:
                templates.append(
                    ResourceTemplate(
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
                )
            except Exception:
                continue
        return templates

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