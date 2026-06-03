from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.runtime.executor import runtime_executor
from app.schemas.resource import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
)
from app.services.postgres_store import store


router = APIRouter()


@router.post("/projects/{project_id}/sessions")
def create_chat_session(
    project_id: str,
    payload: ChatSessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    return store.create_chat_session(db, project_id, user_id, payload.title)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
def send_message(
    session_id: str,
    payload: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    session = store.get_chat_session_for_user(db, session_id, user_id)

    model_provider: str | None = None
    model_name: str | None = None
    system_prompt: str | None = None
    if payload.agent_id:
        agent_resource = store.get_agent_resource_for_project(db, session.project_id, payload.agent_id)
        model_provider = agent_resource.model_provider
        model_name = agent_resource.model_name
        system_prompt = (agent_resource.config or {}).get("system_prompt")

    store.append_chat_message(db, session_id, role="user", text=payload.text)
    answer = runtime_executor.run_chat(
        payload.text,
        model_provider=model_provider,
        model_name=model_name,
        system_prompt=system_prompt,
    )
    store.append_chat_message(db, session_id, role="assistant", text=answer)
    return ChatMessageResponse(session_id=session_id, role="assistant", text=answer)
