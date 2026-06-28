from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.runtime.provider_connections import (
    ProviderConnectionCredentials,
    list_openai_compatible_models,
    test_openai_compatible_chat,
)
from app.schemas.provider_connection import (
    ProviderConnectionCreate,
    ProviderConnectionRecord,
    ProviderConnectionTestRequest,
    ProviderConnectionTestResponse,
    ProviderConnectionUpdate,
    ProviderModelsProbeRequest,
    ProviderModelsProbeResponse,
    SavedProviderConnectionTestRequest,
)
from app.services.postgres_store import store


router = APIRouter()


def _is_missing_provider_connections_table(exc: ProgrammingError) -> bool:
    return "provider_connections" in str(exc)


def _provider_connections_migration_error(exc: ProgrammingError) -> HTTPException:
    if _is_missing_provider_connections_table(exc):
        return HTTPException(
            status_code=503,
            detail="Provider connections table is missing. Run database migrations: alembic upgrade head",
        )
    return HTTPException(status_code=500, detail="Provider connections storage error")


def _credentials_from_probe(payload: ProviderModelsProbeRequest) -> ProviderConnectionCredentials:
    return ProviderConnectionCredentials(
        provider_type=(payload.provider_type or "openai_compatible").strip().lower(),
        base_url=payload.base_url,
        api_key=payload.api_key,
    )


@router.post("/projects/{project_id}/probe-models", response_model=ProviderModelsProbeResponse)
def probe_provider_models(
    project_id: str,
    payload: ProviderModelsProbeRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProviderModelsProbeResponse:
    store.assert_project_member(db, project_id, user_id)
    try:
        models = list_openai_compatible_models(_credentials_from_probe(payload))
        return ProviderModelsProbeResponse(ok=True, models=models)
    except Exception as exc:
        return ProviderModelsProbeResponse(ok=False, models=[], error=str(exc))


@router.post("/projects/{project_id}/test", response_model=ProviderConnectionTestResponse)
def test_provider_connection_draft(
    project_id: str,
    payload: ProviderConnectionTestRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProviderConnectionTestResponse:
    store.assert_project_member(db, project_id, user_id)
    try:
        output = test_openai_compatible_chat(
            _credentials_from_probe(payload),
            model_name=payload.model_name,
            text=payload.text or "ping",
        )
        return ProviderConnectionTestResponse(
            ok=True,
            model_name=payload.model_name,
            output_preview=output[:500],
        )
    except Exception as exc:
        return ProviderConnectionTestResponse(ok=False, model_name=payload.model_name, error=str(exc))


@router.get("/projects/{project_id}", response_model=list[ProviderConnectionRecord])
def list_provider_connections(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[ProviderConnectionRecord]:
    try:
        return store.list_provider_connections(db, project_id=project_id, actor=user_id)
    except ProgrammingError as exc:
        raise _provider_connections_migration_error(exc) from exc


@router.post("/projects/{project_id}", response_model=ProviderConnectionRecord)
def create_provider_connection(
    project_id: str,
    payload: ProviderConnectionCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProviderConnectionRecord:
    if not payload.default_model:
        raise HTTPException(status_code=400, detail="default_model is required")
    try:
        test_openai_compatible_chat(
            _credentials_from_probe(payload),
            model_name=payload.default_model,
            text="ping",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Provider test failed: {exc}") from exc

    connection = store.add_provider_connection(db, project_id=project_id, owner_id=user_id, payload=payload)
    return store.mark_provider_connection_test_result(
        db,
        connection_id=connection.id,
        actor=user_id,
        ok=True,
        models=payload.model_list_cache,
    )


@router.get("/{connection_id}", response_model=ProviderConnectionRecord)
def get_provider_connection(
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProviderConnectionRecord:
    return store.get_provider_connection(db, connection_id=connection_id, actor=user_id)


@router.patch("/{connection_id}", response_model=ProviderConnectionRecord)
def update_provider_connection(
    connection_id: str,
    payload: ProviderConnectionUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProviderConnectionRecord:
    return store.update_provider_connection(db, connection_id=connection_id, actor=user_id, payload=payload)


@router.post("/{connection_id}/test", response_model=ProviderConnectionTestResponse)
def test_saved_provider_connection(
    connection_id: str,
    payload: SavedProviderConnectionTestRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProviderConnectionTestResponse:
    runtime_config = store.get_provider_connection_runtime_config(db, connection_id=connection_id, actor=user_id)
    try:
        output = test_openai_compatible_chat(
            ProviderConnectionCredentials(
                provider_type=runtime_config["provider_type"],
                base_url=runtime_config["base_url"],
                api_key=runtime_config["api_key"],
            ),
            model_name=payload.model_name,
            text=payload.text or "ping",
        )
        store.mark_provider_connection_test_result(db, connection_id=connection_id, actor=user_id, ok=True)
        return ProviderConnectionTestResponse(
            ok=True,
            model_name=payload.model_name,
            output_preview=output[:500],
        )
    except Exception as exc:
        error = str(exc)
        store.mark_provider_connection_test_result(db, connection_id=connection_id, actor=user_id, ok=False, error=error)
        return ProviderConnectionTestResponse(ok=False, model_name=payload.model_name, error=error)


@router.delete("/{connection_id}")
def delete_provider_connection(
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    store.delete_provider_connection(db, connection_id=connection_id, actor=user_id)
    return {"ok": True}
