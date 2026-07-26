"""Skill processing and execution service"""

import json
import os
import re
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import jsonschema

from app.db.session import SessionLocal
from app.db.models import SkillMetadataModel, ResourceModel
from sqlalchemy import select
from sqlalchemy.orm import Session


SKILL_UPLOADS_ROOT = Path(
    os.getenv(
        "SKILL_UPLOADS_ROOT",
        str(Path(__file__).resolve().parents[2] / "data" / "skills")
    )
)


def _normalize_uploaded_paths(paths: list[str]) -> list[str]:
    normalized: list[str] = []
    for path in paths:
        clean = path.replace("\\", "/").strip("/")
        if clean and not clean.endswith("/"):
            normalized.append(clean)
    return sorted(set(normalized))


def _persist_skill_upload_manifest(skill_id: str, uploaded_files: list[str]) -> None:
    skill_dir = SKILL_UPLOADS_ROOT / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = skill_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"uploaded_files": uploaded_files}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _persist_extracted_skill_files(skill_id: str, extracted_dir: Path) -> None:
    skill_files_dir = SKILL_UPLOADS_ROOT / skill_id / "files"
    if skill_files_dir.exists():
        shutil.rmtree(skill_files_dir, ignore_errors=True)
    skill_files_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(extracted_dir, skill_files_dir)


def _read_skill_upload_manifest(skill_id: str) -> list[str]:
    manifest_path = SKILL_UPLOADS_ROOT / skill_id / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = payload.get("uploaded_files", [])
        if isinstance(files, list):
            return [str(item) for item in files]
    except Exception:
        return []
    return []


def get_skill_uploaded_file_content(skill_id: str, relative_path: str, max_chars: int = 200000) -> Dict[str, Any]:
    normalized = relative_path.replace("\\", "/").strip("/")
    if not normalized or ".." in Path(normalized).parts:
        raise ValueError("Invalid file path")

    files_root = (SKILL_UPLOADS_ROOT / skill_id / "files").resolve()
    target = (files_root / normalized).resolve()

    try:
        target.relative_to(files_root)
    except ValueError as exc:
        raise ValueError("Invalid file path") from exc

    if not target.exists() or not target.is_file():
        raise FileNotFoundError("File not found")

    raw = target.read_bytes()
    truncated = False
    if len(raw) > max_chars:
        raw = raw[:max_chars]
        truncated = True

    try:
        content = raw.decode("utf-8")
        return {
            "path": normalized,
            "content": content,
            "is_text": True,
            "encoding": "utf-8",
            "truncated": truncated,
            "size_bytes": target.stat().st_size,
        }
    except UnicodeDecodeError:
        return {
            "path": normalized,
            "content": "",
            "is_text": False,
            "encoding": None,
            "truncated": False,
            "size_bytes": target.stat().st_size,
        }


def delete_skill_artifacts(skill_id: str) -> None:
    """Delete persisted skill upload files and manifest for a skill resource."""
    skill_dir = SKILL_UPLOADS_ROOT / skill_id
    if skill_dir.exists():
        shutil.rmtree(skill_dir, ignore_errors=True)


def parse_skill_md(skill_md_content: str) -> Dict[str, Any]:
    """
    Parse SKILL.md file and extract frontmatter (YAML) and markdown content
    
    Expected format:
    ---
    name: skill-name
    version: 1.0.0
    entrypoint: "scripts/main:execute"
    input_schema: {...}
    output_schema: {...}
    requirements: {...}
    author: "name"
    capabilities: [...]
    ---
    
    # Markdown Documentation
    ...
    
    Args:
        skill_md_content: Raw SKILL.md file content
        
    Returns:
        Dict with keys: frontmatter (dict), markdown (str)
    """
    # Split frontmatter and markdown by --- delimiters
    lines = skill_md_content.split('\n')
    
    if not lines or lines[0].strip() != '---':
        raise ValueError("SKILL.md must start with --- (YAML frontmatter)")
    
    # Find closing --- (frontmatter end)
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break
    
    if end_idx == -1:
        raise ValueError("SKILL.md frontmatter not closed with ---")
    
    # Extract frontmatter and markdown
    frontmatter_lines = lines[1:end_idx]
    markdown_lines = lines[end_idx + 1:]
    
    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load('\n'.join(frontmatter_lines))
        if frontmatter is None:
            frontmatter = {}
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse SKILL.md frontmatter: {e}")
    
    # Markdown content (skip leading/trailing empty lines)
    markdown = '\n'.join(markdown_lines).strip()
    
    return {
        "frontmatter": frontmatter,
        "markdown": markdown
    }


def validate_skill_metadata(frontmatter: Dict[str, Any]) -> None:
    """
    Validate required fields in Skill metadata
    
    Required fields:
    - name: str

    Optional fields are validated only when provided:
    - version: str (semantic versioning)
    - author: str
    - entrypoint: str
    - capabilities: list|dict
    - requirements: dict|list
    - input_schema/output_schema: dict
    
    Args:
        frontmatter: Parsed YAML frontmatter dict
        
    Raises:
        ValueError: If required fields are missing
    """
    if not isinstance(frontmatter, dict):
        raise ValueError("SKILL.md frontmatter must be a YAML object")

    if "name" not in frontmatter:
        raise ValueError("Missing required field in SKILL.md: name")
    if not isinstance(frontmatter["name"], str):
        raise ValueError("Field 'name' must be a string")

    optional_fields = {
        "version": str,
        "author": str,
        "entrypoint": str,
        "capabilities": (list, dict),
        "requirements": (dict, list),
    }

    for field, expected_type in optional_fields.items():
        if field in frontmatter and frontmatter[field] is not None and not isinstance(frontmatter[field], expected_type):
            raise ValueError(f"Field '{field}' has incorrect type: expected {expected_type}, got {type(frontmatter[field])}")
    
    # Validate schema fields if present
    if "input_schema" in frontmatter and frontmatter["input_schema"]:
        if not isinstance(frontmatter["input_schema"], dict):
            raise ValueError("input_schema must be a JSON Schema object (dict)")
    
    if "output_schema" in frontmatter and frontmatter["output_schema"]:
        if not isinstance(frontmatter["output_schema"], dict):
            raise ValueError("output_schema must be a JSON Schema object (dict)")
    
    # Validate entrypoint format only when provided: "scripts/main:execute"
    entrypoint = frontmatter.get("entrypoint")
    if entrypoint and not re.match(r'^scripts/[\w_]+:[\w_]+$', entrypoint):
        raise ValueError(
            f"Invalid entrypoint format: '{entrypoint}'. "
            "Expected format: 'scripts/module_name:function_name'"
        )
    
    # Validate version format only when provided (semantic versioning)
    version = frontmatter.get("version")
    if version and not re.match(r'^\d+\.\d+\.\d+', version):
        raise ValueError(
            f"Invalid version format: '{version}'. "
            "Expected semantic versioning: major.minor.patch"
        )


def validate_input_output(
    data: Dict[str, Any],
    schema: Optional[Dict[str, Any]]
) -> None:
    """
    Validate input/output data against JSON Schema
    
    Args:
        data: Data to validate
        schema: JSON Schema dict (can be None)
        
    Raises:
        jsonschema.ValidationError: If validation fails
    """
    if schema is None:
        return
    
    if not schema:  # Empty schema
        return
    
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Schema validation failed: {e.message}")


async def process_skill_upload(
    db: Session,
    project_id: str,
    owner_id: str,
    skill_name: str,
    skill_id: str,
    file_path: str,
    storage_type: str = "local"
) -> Dict[str, Any]:
    """
    Process uploaded Skill (extract from zip, parse SKILL.md, validate)
    
    Args:
        db: Database session
        project_id: Project ID
        owner_id: Owner user ID
        skill_name: Skill resource name
        skill_id: Skill resource ID
        file_path: Path to uploaded skill zip file
        storage_type: "local" | "git" | "s3"
        
    Returns:
        Dict with parsed metadata and content
        
    Raises:
        ValueError: If skill format or content is invalid
    """
    # Extract zip to temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            uploaded_files = _normalize_uploaded_paths(zip_ref.namelist())
            zip_ref.extractall(temp_dir)

        # Persist file manifest for Manage page visibility.
        _persist_skill_upload_manifest(skill_id, uploaded_files)
        _persist_extracted_skill_files(skill_id, Path(temp_dir))
        
        # Find SKILL.md. Folder uploads often include a top-level directory
        # (e.g. my-skill/SKILL.md), so search recursively.
        root_skill_md = Path(temp_dir) / "SKILL.md"
        if root_skill_md.exists():
            skill_md_path = root_skill_md
        else:
            candidates = list(Path(temp_dir).rglob("SKILL.md"))
            if not candidates:
                raise ValueError("SKILL.md not found in uploaded skill package")
            # Prefer the shallowest SKILL.md when multiple are present.
            skill_md_path = min(candidates, key=lambda p: len(p.relative_to(temp_dir).parts))
        
        # Read and parse SKILL.md
        skill_md_content = skill_md_path.read_text(encoding='utf-8')
        parsed = parse_skill_md(skill_md_content)
        
        # Validate metadata
        validate_skill_metadata(parsed["frontmatter"])
        
        frontmatter = parsed["frontmatter"]
        
        # Prepare metadata for storage
        metadata = {
            "author": frontmatter.get("author", owner_id),
            "version": frontmatter.get("version") or "0.1.0",
            "entrypoint": frontmatter.get("entrypoint") or "scripts/main:execute",
            "capabilities": frontmatter.get("capabilities", []),
            "requirements": frontmatter.get("requirements", {}),
            "input_schema": frontmatter.get("input_schema", {}),
            "output_schema": frontmatter.get("output_schema", {}),
            "storage_type": storage_type,
            "repo_url": frontmatter.get("repo_url"),
            "repo_branch": frontmatter.get("repo_branch", "main"),
            "skill_md_content": parsed["markdown"],
            "status": frontmatter.get("status", "active"),
        }

        response_metadata = {
            **metadata,
            "uploaded_files": uploaded_files,
        }
        
        # Store skill metadata in database (upsert by skill_id).
        skill_metadata = db.scalar(
            select(SkillMetadataModel).where(SkillMetadataModel.skill_id == skill_id)
        )
        if skill_metadata:
            skill_metadata.project_id = project_id
            for key, value in metadata.items():
                setattr(skill_metadata, key, value)
        else:
            skill_metadata = SkillMetadataModel(
                skill_id=skill_id,
                project_id=project_id,
                **metadata
            )
            db.add(skill_metadata)
        db.commit()
        
        return response_metadata
        
    finally:
        # Cleanup temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


async def get_skill_metadata(
    db: Session,
    skill_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get Skill metadata by skill resource ID
    
    Args:
        db: Database session
        skill_id: Skill resource ID
        
    Returns:
        Skill metadata dict or None if not found
    """
    skill_meta = db.scalar(select(SkillMetadataModel).where(
        SkillMetadataModel.skill_id == skill_id
    ))
    
    if not skill_meta:
        return None
    
    return {
        "skill_id": skill_meta.skill_id,
        "project_id": skill_meta.project_id,
        "storage_type": skill_meta.storage_type,
        "repo_url": skill_meta.repo_url,
        "repo_branch": skill_meta.repo_branch,
        "author": skill_meta.author,
        "version": skill_meta.version,
        "capabilities": skill_meta.capabilities,
        "requirements": skill_meta.requirements,
        "entrypoint": skill_meta.entrypoint,
        "input_schema": skill_meta.input_schema,
        "output_schema": skill_meta.output_schema,
        "skill_md_content": skill_meta.skill_md_content,
        "status": skill_meta.status,
        "created_at": skill_meta.created_at,
        "updated_at": skill_meta.updated_at,
        "uploaded_files": _read_skill_upload_manifest(skill_id),
    }


async def list_skills(
    db: Session,
    project_id: str,
    status: Optional[str] = None
) -> list[Dict[str, Any]]:
    """
    List all skills in a project
    
    Args:
        db: Database session
        project_id: Project ID
        status: Filter by status ("active" | "inactive" | "deprecated")
        
    Returns:
        List of skill metadata dicts
    """
    query = select(SkillMetadataModel).where(
        SkillMetadataModel.project_id == project_id
    )
    
    if status:
        query = query.where(SkillMetadataModel.status == status)
    
    skills = db.scalars(query).all()
    
    return [
        {
            "skill_id": skill.skill_id,
            "version": skill.version,
            "author": skill.author,
            "entrypoint": skill.entrypoint,
            "capabilities": skill.capabilities,
            "status": skill.status,
            "created_at": skill.created_at,
        }
        for skill in skills
    ]
