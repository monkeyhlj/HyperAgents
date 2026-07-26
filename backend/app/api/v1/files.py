from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_current_user_id
from app.services.user_file_service import user_file_service

router = APIRouter(tags=["files"])


@router.get("/me")
def list_my_files(user_id: str = Depends(get_current_user_id)) -> dict:
    return {"files": user_file_service.list_files(user_id)}


@router.get("/me/download")
def download_my_file(
    path: str = Query(...),
    user_id: str = Depends(get_current_user_id),
):
    try:
        file_path = user_file_service.get_file_for_download(user_id, path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FileResponse(path=str(file_path), filename=file_path.name, media_type="application/octet-stream")


@router.post("/me/upload")
async def upload_my_files(
    files: list[UploadFile] = File(...),
    target_dir: str | None = Form(default=None),
    user_id: str = Depends(get_current_user_id),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    base_dir = (target_dir or f"uploads/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}").strip("/")
    uploaded_paths: list[str] = []

    try:
        for file in files:
            if not file.filename:
                continue
            content = await file.read()
            relative_path = f"{base_dir}/{file.filename}".replace("\\", "/")
            uploaded_paths.append(user_file_service.save_bytes_file(user_id, relative_path, content))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"uploaded_paths": uploaded_paths, "count": len(uploaded_paths), "base_dir": base_dir}
