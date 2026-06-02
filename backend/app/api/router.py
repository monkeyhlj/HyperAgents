from fastapi import APIRouter

from app.api.v1 import chat, projects, resources


api_router = APIRouter()
api_router.include_router(projects.router, prefix="/v1/projects", tags=["projects"])
api_router.include_router(resources.router, prefix="/v1/resources", tags=["resources"])
api_router.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
