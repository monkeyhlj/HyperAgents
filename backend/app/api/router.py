from fastapi import APIRouter

from app.api.v1 import auth, chat, files, memory, projects, provider_connections, registry, resources, knowledge, skills


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/v1/projects", tags=["projects"])
api_router.include_router(resources.router, prefix="/v1/resources", tags=["resources"])
api_router.include_router(provider_connections.router, prefix="/v1/provider-connections", tags=["provider-connections"])
api_router.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
api_router.include_router(files.router, prefix="/v1/files", tags=["files"])
api_router.include_router(memory.router, prefix="/v1/memory", tags=["memory"])
api_router.include_router(registry.router, prefix="/v1/registry", tags=["registry"])
api_router.include_router(knowledge.router, prefix="/v1/knowledge", tags=["knowledge"])
api_router.include_router(skills.router, prefix="/v1/skills", tags=["skills"])

