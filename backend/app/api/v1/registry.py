from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import httpx

from app.api.deps import get_current_user_id, get_db
from app.models.enums import ResourceKind, Visibility
from app.schemas.registry import MCPProbeRequest, MCPProbeResponse, RegistryItemCreate, RegistryListResponse
from app.schemas.resource import Resource
from app.services.postgres_store import store


router = APIRouter()
_ALLOWED_REGISTRY_KINDS = {ResourceKind.MCP, ResourceKind.TOOL, ResourceKind.SKILL}


def _assert_registry_kind(kind: ResourceKind) -> None:
    if kind not in _ALLOWED_REGISTRY_KINDS:
        raise HTTPException(status_code=400, detail="Registry kind must be one of: mcp, tool, skill")


@router.post("/projects/{project_id}/{kind}", response_model=Resource)
def create_registry_item(
    project_id: str,
    kind: ResourceKind,
    payload: RegistryItemCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Resource:
    _assert_registry_kind(kind)
    store.assert_project_member(db, project_id, user_id)
    return store.add_resource(
        db=db,
        project_id=project_id,
        owner_id=user_id,
        kind=kind,
        name=payload.name,
        description=payload.description,
        visibility=payload.visibility,
        model_provider=payload.model_provider,
        model_name=payload.model_name,
        config=payload.config,
    )


@router.get("/projects/{project_id}/{kind}", response_model=RegistryListResponse)
def list_registry_items(
    project_id: str,
    kind: ResourceKind,
    visibility: Visibility | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> RegistryListResponse:
    _assert_registry_kind(kind)
    items = store.list_project_resources(db, project_id, user_id, kind, visibility)
    return RegistryListResponse(items=items, total=len(items))


@router.get("/public/{kind}", response_model=RegistryListResponse)
def list_public_registry_items(
    kind: ResourceKind,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> RegistryListResponse:
    _assert_registry_kind(kind)
    items = store.list_public_resources(db, kind, limit)
    return RegistryListResponse(items=items, total=len(items))


@router.post("/mcp/probe", response_model=MCPProbeResponse)
def probe_mcp_server(
    payload: MCPProbeRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MCPProbeResponse:
    store.assert_project_member(db, payload.project_id, user_id)

    config = dict(payload.config or {})
    transport = str(config.get("transport") or "streamable_http").strip().lower()
    endpoint_url = str(config.get("endpoint_url") or "").strip()

    if transport != "streamable_http":
        return MCPProbeResponse(
            ok=False,
            transport=transport,
            endpoint_url=endpoint_url or None,
            error="Only streamable_http probe is supported currently",
        )

    if not endpoint_url:
        return MCPProbeResponse(
            ok=False,
            transport=transport,
            error="endpoint_url is required for streamable_http transport",
        )

    health_ok = False
    tools_ok = False
    tools: list[str] = []
    timeout_seconds = float(config.get("timeout_seconds") or 8)

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            health_response = client.get(f"{endpoint_url.rstrip('/')}/health")
            health_ok = health_response.status_code == 200

            tools_response = client.get(f"{endpoint_url.rstrip('/')}/tools")
            if tools_response.status_code == 200:
                raw = tools_response.json()
                if isinstance(raw, dict):
                    tool_items = raw.get("tools") or []
                elif isinstance(raw, list):
                    tool_items = raw
                else:
                    tool_items = []
                tools = [
                    str(item.get("name") or "").strip()
                    for item in tool_items
                    if isinstance(item, dict) and str(item.get("name") or "").strip()
                ]
                tools_ok = True
    except Exception as exc:
        return MCPProbeResponse(
            ok=False,
            transport=transport,
            endpoint_url=endpoint_url,
            health_ok=health_ok,
            tools_ok=tools_ok,
            tools=tools,
            error=str(exc),
        )

    return MCPProbeResponse(
        ok=health_ok and tools_ok,
        transport=transport,
        endpoint_url=endpoint_url,
        health_ok=health_ok,
        tools_ok=tools_ok,
        tools=tools,
        error=None if (health_ok and tools_ok) else "Health or tools probe failed",
    )
