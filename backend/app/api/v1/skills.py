"""Skills API endpoints."""
import logging
import os
import tempfile
from typing import Optional, List

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.db.models import (
    ResourceModel,
    SkillMetadataModel,
    AgentSkillBindingModel,
    SkillExecutionModel,
)
from app.models.enums import ResourceKind
from app.runtime.skill_service import (
    parse_skill_md,
    validate_skill_metadata,
    process_skill_upload,
    get_skill_metadata,
    get_skill_uploaded_file_content,
    list_skills,
)
from app.schemas.resource import Resource
from app.services.postgres_store import store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["skills"])


# Request/Response models
class SkillBindingRequest(BaseModel):
    skill_id: str
    priority: int = 0
    instance_config: dict = {}


@router.post("/{skill_id}/upload")
async def upload_skill(
    skill_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Upload a Skill package (zip file containing SKILL.md and scripts/).
    
    Expected structure:
    skill-name.zip/
    ├── SKILL.md           # Required
    ├── scripts/
    │   ├── main.py
    │   └── utils.py
    ├── references/        # Optional
    └── assets/            # Optional
    """
    # Verify skill resource exists and user has access
    skill_resource = db.scalar(select(ResourceModel).where(
        ResourceModel.id == skill_id
    ))
    
    if not skill_resource:
        raise HTTPException(status_code=404, detail="Skill resource not found")
    
    if skill_resource.kind != ResourceKind.SKILL.value:
        raise HTTPException(status_code=400, detail="Resource is not a skill")
    
    # Check user permission (must be project member)
    store.assert_project_member(db, skill_resource.project_id, user_id)
    
    # Validate file is zip
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="File must be a .zip archive"
        )
    
    try:
        # Save uploaded file temporarily
        upload_dir = f"/tmp/skills/{skill_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process skill upload
        metadata = await process_skill_upload(
            db=db,
            project_id=skill_resource.project_id,
            owner_id=user_id,
            skill_name=skill_resource.name,
            skill_id=skill_id,
            file_path=file_path,
            storage_type="local"
        )
        
        return {
            "skill_id": skill_id,
            "message": "Skill uploaded successfully",
            "metadata": metadata
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading skill: {e}")
        raise HTTPException(status_code=500, detail="Failed to process skill upload")
    finally:
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/{skill_id}/upload-folder")
async def upload_skill_folder(
    skill_id: str,
    files: List[UploadFile] = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Upload Skill files directly as a folder structure.
    
    Expected:
    - Multiple files with relative paths
    - Must include SKILL.md
    - Optional: scripts/, references/, assets/, etc.
    """
    import zipfile
    
    # Verify skill resource exists and user has access
    skill_resource = db.scalar(select(ResourceModel).where(
        ResourceModel.id == skill_id
    ))
    
    if not skill_resource:
        raise HTTPException(status_code=404, detail="Skill resource not found")
    
    if skill_resource.kind != ResourceKind.SKILL.value:
        raise HTTPException(status_code=400, detail="Resource is not a skill")
    
    # Check user permission (must be project member)
    store.assert_project_member(db, skill_resource.project_id, user_id)
    
    # Validate SKILL.md exists
    has_skill_md = any(
        file.filename and file.filename.endswith("SKILL.md")
        for file in files
    )
    
    if not has_skill_md:
        raise HTTPException(
            status_code=400,
            detail="Folder must contain SKILL.md file"
        )
    
    try:
        # Create temporary directory for files
        upload_dir = f"/tmp/skills/{skill_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save all files temporarily
        file_paths = {}
        for file in files:
            if not file.filename:
                continue
                
            # Use filename as relative path (e.g., SKILL.md, scripts/main.py)
            relative_path = file.filename
            file_full_path = os.path.join(upload_dir, relative_path)
            
            # Create subdirectories if needed
            os.makedirs(os.path.dirname(file_full_path), exist_ok=True)
            
            # Save file
            content = await file.read()
            with open(file_full_path, "wb") as f:
                f.write(content)
            
            file_paths[relative_path] = file_full_path
        
        # Create a zip file from the uploaded files
        zip_path = os.path.join(upload_dir, f"{skill_id}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for relative_path, full_path in file_paths.items():
                arcname = relative_path.replace("\\", "/")
                zipf.write(full_path, arcname=arcname)
        
        # Process skill upload using the created zip
        metadata = await process_skill_upload(
            db=db,
            project_id=skill_resource.project_id,
            owner_id=user_id,
            skill_name=skill_resource.name,
            skill_id=skill_id,
            file_path=zip_path,
            storage_type="local"
        )
        
        return {
            "skill_id": skill_id,
            "message": "Skill folder uploaded successfully",
            "metadata": metadata
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading skill folder: {e}")
        raise HTTPException(status_code=500, detail="Failed to process skill folder upload")
    finally:
        # Cleanup temp files and directory
        try:
            import shutil
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir)
        except Exception as cleanup_err:
            logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")


@router.get("/{skill_id}")
async def get_skill_detail(
    skill_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get skill metadata and documentation."""
    # Verify skill resource exists and user has access
    skill_resource = db.scalar(select(ResourceModel).where(
        ResourceModel.id == skill_id
    ))
    
    if not skill_resource:
        raise HTTPException(status_code=404, detail="Skill resource not found")
    
    # Check user permission
    store.assert_project_member(db, skill_resource.project_id, user_id)
    
    # Get skill metadata (may not exist yet if not uploaded)
    metadata = await get_skill_metadata(db, skill_id)
    
    # Combine resource and metadata (metadata can be None)
    return {
        "id": skill_resource.id,
        "name": skill_resource.name,
        "kind": skill_resource.kind,
        "project_id": skill_resource.project_id,
        "owner_id": skill_resource.owner_id,
        "visibility": skill_resource.visibility,
        "description": skill_resource.description,
        "created_at": skill_resource.created_at,
        "updated_at": skill_resource.updated_at,
        **(metadata or {})
    }


@router.get("/{skill_id}/files/content")
async def get_skill_file_content(
    skill_id: str,
    path: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get uploaded skill file content for preview."""
    skill_resource = db.scalar(select(ResourceModel).where(
        ResourceModel.id == skill_id
    ))
    if not skill_resource:
        raise HTTPException(status_code=404, detail="Skill resource not found")

    store.assert_project_member(db, skill_resource.project_id, user_id)

    try:
        return get_skill_uploaded_file_content(skill_id, path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/skills")
async def list_project_skills(
    project_id: str,
    status: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List all skills in a project."""
    # Check user permission
    store.assert_project_member(db, project_id, user_id)
    
    # List skills
    skills = await list_skills(db, project_id, status)
    
    return {
        "project_id": project_id,
        "skills": skills
    }


@router.post("/{skill_id}/test")
async def test_skill(
    skill_id: str,
    input_data: dict,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Test a skill by executing it with provided input.
    
    This is a basic test endpoint. Full execution requires proper sandboxing.
    """
    # Verify skill exists and user has access
    skill_resource = db.scalar(select(ResourceModel).where(
        ResourceModel.id == skill_id
    ))
    
    if not skill_resource:
        raise HTTPException(status_code=404, detail="Skill resource not found")
    
    # Check user permission
    store.assert_project_member(db, skill_resource.project_id, user_id)
    
    # Get skill metadata
    metadata = await get_skill_metadata(db, skill_id)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="Skill metadata not found")
    
    # TODO: Implement actual skill execution with sandboxing
    # For now, just validate input schema
    from app.runtime.skill_service import validate_input_output
    
    try:
        validate_input_output(input_data, metadata.get("input_schema"))
        
        return {
            "skill_id": skill_id,
            "status": "pending",
            "message": "Test execution started (full implementation pending)"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agents/{agent_id}/skills")
async def bind_skill_to_agent(
    agent_id: str,
    binding_request: SkillBindingRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Bind a skill to an agent."""
    skill_id = binding_request.skill_id
    priority = binding_request.priority
    instance_config = binding_request.instance_config or {}
    # Verify agent exists
    agent_resource = db.scalar(select(ResourceModel).where(
        ResourceModel.id == agent_id
    ))
    
    if not agent_resource:
        raise HTTPException(status_code=404, detail="Agent resource not found")
    
    if agent_resource.kind != ResourceKind.AGENT.value:
        raise HTTPException(status_code=400, detail="Resource is not an agent")
    
    # Verify skill exists
    skill_resource = db.scalar(select(ResourceModel).where(
        ResourceModel.id == skill_id
    ))
    
    if not skill_resource:
        raise HTTPException(status_code=404, detail="Skill resource not found")
    
    if skill_resource.kind != ResourceKind.SKILL.value:
        raise HTTPException(status_code=400, detail="Resource is not a skill")
    
    # Both must be in same project
    if agent_resource.project_id != skill_resource.project_id:
        raise HTTPException(
            status_code=400,
            detail="Agent and skill must be in the same project"
        )
    
    # Check user permission
    store.assert_project_member(db, agent_resource.project_id, user_id)
    
    # Check if binding already exists
    existing = db.scalar(select(AgentSkillBindingModel).where(
        (AgentSkillBindingModel.agent_id == agent_id) &
        (AgentSkillBindingModel.skill_id == skill_id)
    ))
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Skill is already bound to this agent"
        )
    
    # Create binding
    binding = AgentSkillBindingModel(
        agent_id=agent_id,
        skill_id=skill_id,
        project_id=agent_resource.project_id,
        priority=priority,
        instance_config=instance_config or {}
    )
    db.add(binding)
    db.commit()
    
    return {
        "binding_id": binding.id,
        "agent_id": agent_id,
        "skill_id": skill_id,
        "message": "Skill bound to agent successfully"
    }


@router.delete("/agents/{agent_id}/skills/{skill_id}")
async def unbind_skill_from_agent(
    agent_id: str,
    skill_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Unbind a skill from an agent."""
    # Verify agent exists and user has permission
    agent_resource = db.scalar(select(ResourceModel).where(
        ResourceModel.id == agent_id
    ))
    
    if not agent_resource:
        raise HTTPException(status_code=404, detail="Agent resource not found")
    
    store.assert_project_member(db, agent_resource.project_id, user_id)
    
    # Find and delete binding
    binding = db.scalar(select(AgentSkillBindingModel).where(
        (AgentSkillBindingModel.agent_id == agent_id) &
        (AgentSkillBindingModel.skill_id == skill_id)
    ))
    
    if not binding:
        raise HTTPException(status_code=404, detail="Binding not found")
    
    db.delete(binding)
    db.commit()
    
    return {
        "message": "Skill unbound from agent successfully"
    }


@router.get("/agents/{agent_id}/skills")
async def list_agent_skills(
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List all skills bound to an agent."""
    # Verify agent exists and user has permission
    agent_resource = db.scalar(select(ResourceModel).where(
        ResourceModel.id == agent_id
    ))
    
    if not agent_resource:
        raise HTTPException(status_code=404, detail="Agent resource not found")
    
    store.assert_project_member(db, agent_resource.project_id, user_id)
    
    # Get bindings
    bindings = db.scalars(select(AgentSkillBindingModel).where(
        AgentSkillBindingModel.agent_id == agent_id
    ).order_by(AgentSkillBindingModel.priority.desc())).all()
    
    # Fetch skill details for each binding
    skills = []
    for binding in bindings:
        skill = db.scalar(select(ResourceModel).where(
            ResourceModel.id == binding.skill_id
        ))
        
        if skill:
            metadata = await get_skill_metadata(db, binding.skill_id)
            skills.append({
                "binding_id": binding.id,
                "skill_id": binding.skill_id,
                "skill_name": skill.name,
                "priority": binding.priority,
                "enabled": binding.enabled,
                "instance_config": binding.instance_config,
                **metadata
            })
    
    return {
        "agent_id": agent_id,
        "skills": skills
    }


@router.get("/{skill_id}/agents")
async def list_skill_bindings(
    skill_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List all agents that have this skill bound."""
    # Verify skill exists and user has permission
    skill_resource = db.scalar(select(ResourceModel).where(
        ResourceModel.id == skill_id
    ))
    
    if not skill_resource:
        raise HTTPException(status_code=404, detail="Skill resource not found")
    
    store.assert_project_member(db, skill_resource.project_id, user_id)
    
    # Get bindings
    bindings = db.scalars(select(AgentSkillBindingModel).where(
        AgentSkillBindingModel.skill_id == skill_id
    ).order_by(AgentSkillBindingModel.priority.desc())).all()
    
    # Fetch agent details for each binding
    agents = []
    for binding in bindings:
        agent = db.scalar(select(ResourceModel).where(
            ResourceModel.id == binding.agent_id
        ))
        
        if agent:
            agents.append({
                "binding_id": binding.id,
                "agent_id": binding.agent_id,
                "agent_name": agent.name,
                "priority": binding.priority,
                "enabled": binding.enabled,
                "instance_config": binding.instance_config,
            })
    
    return {
        "skill_id": skill_id,
        "agents": agents
    }
