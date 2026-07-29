from __future__ import annotations

import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Any


USER_FILES_ROOT = Path(
    os.getenv(
        "USER_FILES_ROOT",
        str(Path(__file__).resolve().parents[2] / "data" / "user_files"),
    )
)


class UserFileService:
    @staticmethod
    def _user_root(user_id: str) -> Path:
        root = USER_FILES_ROOT / str(user_id)
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _resolve_user_path(user_id: str, relative_path: str) -> Path:
        normalized = str(relative_path or "").replace("\\", "/").strip("/")
        if not normalized or ".." in Path(normalized).parts:
            raise ValueError("Invalid file path")

        root = UserFileService._user_root(user_id).resolve()
        target = (root / normalized).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("Invalid file path") from exc
        return target

    @staticmethod
    def list_files(user_id: str) -> list[dict[str, Any]]:
        root = UserFileService._user_root(user_id)
        files: list[dict[str, Any]] = []

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            stat = path.stat()
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size_bytes": stat.st_size,
                    "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        files.sort(key=lambda item: item["updated_at"], reverse=True)
        return files

    @staticmethod
    def save_text_file(user_id: str, relative_path: str, content: str) -> str:
        target = UserFileService._resolve_user_path(user_id, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target.name

    @staticmethod
    def save_bytes_file(user_id: str, relative_path: str, content: bytes) -> str:
        target = UserFileService._resolve_user_path(user_id, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target.relative_to(UserFileService._user_root(user_id)).as_posix()

    @staticmethod
    def save_generated_files(user_id: str, base_dir: str, generated_files: list[dict[str, Any]]) -> list[str]:
        saved_paths: list[str] = []
        for item in generated_files:
            filename = str(item.get("filename") or item.get("name") or "").strip()
            if not filename:
                continue

            relative = f"{base_dir.strip('/')}/{filename}".strip("/")
            target = UserFileService._resolve_user_path(user_id, relative)
            target.parent.mkdir(parents=True, exist_ok=True)

            if item.get("content_base64"):
                data = base64.b64decode(str(item["content_base64"]))
                target.write_bytes(data)
            else:
                text = str(item.get("content") or "")
                target.write_text(text, encoding="utf-8")

            saved_paths.append(target.relative_to(UserFileService._user_root(user_id)).as_posix())

        return saved_paths

    @staticmethod
    def get_file_for_download(user_id: str, relative_path: str) -> Path:
        target = UserFileService._resolve_user_path(user_id, relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError("File not found")
        return target

    @staticmethod
    def delete_file(user_id: str, relative_path: str) -> str:
        target = UserFileService._resolve_user_path(user_id, relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError("File not found")

        root = UserFileService._user_root(user_id).resolve()
        deleted_path = target.relative_to(root).as_posix()
        target.unlink()

        current = target.parent
        while current != root:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

        return deleted_path


user_file_service = UserFileService()
