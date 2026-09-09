"""JSON-file-backed project storage and generated-project disk/zip management.

Reads app.config.PROJECTS_DIR / GENERATED_DIR at call time (never caches them
at import time) so tests can monkeypatch config for isolated storage.
"""

from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app import config
from app.models.mcp import GeneratedMCPServer, MCPProject
from app.models.project import ProjectMetadata


def _project_path(project_id: str) -> Path:
    return config.PROJECTS_DIR / f"{project_id}.json"


def create_project(source_url: str) -> MCPProject:
    now = datetime.now(timezone.utc)
    project = MCPProject(
        id=uuid.uuid4().hex[:12],
        created_at=now,
        updated_at=now,
        source_url=source_url,
        status="pending",
    )
    save_project(project)
    return project


def save_project(project: MCPProject) -> None:
    config.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    path = _project_path(project.id)
    path.write_text(json.dumps(project.model_dump(mode="json"), indent=2), encoding="utf-8")


def load_project(project_id: str) -> Optional[MCPProject]:
    path = _project_path(project_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return MCPProject.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


def _server_name_for(project: MCPProject) -> str:
    if project.generated and project.generated.get("server_name"):
        return str(project.generated["server_name"])
    if project.design and project.design.get("server_name"):
        return str(project.design["server_name"])
    return "unnamed-mcp-server"


def _tool_count_for(project: MCPProject) -> int:
    if project.generated and "tool_count" in project.generated:
        return int(project.generated["tool_count"] or 0)
    if project.design and project.design.get("tools"):
        return len(project.design["tools"])
    return 0


def list_projects(limit: int = 50) -> list[ProjectMetadata]:
    if not config.PROJECTS_DIR.exists():
        return []

    metadatas: list[ProjectMetadata] = []
    for file_path in config.PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            project = MCPProject.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            continue
        metadatas.append(
            ProjectMetadata(
                id=project.id,
                server_name=_server_name_for(project),
                source_url=project.source_url,
                tool_count=_tool_count_for(project),
                status=project.status,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
        )

    metadatas.sort(key=lambda m: m.updated_at, reverse=True)
    return metadatas[:limit]


def delete_project(project_id: str) -> None:
    path = _project_path(project_id)
    if path.exists():
        path.unlink()

    project_dir = config.GENERATED_DIR / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)

    zip_path = config.GENERATED_DIR / f"{project_id}.zip"
    if zip_path.exists():
        zip_path.unlink()


def save_generated_files_to_disk(project_id: str, server: GeneratedMCPServer) -> Path:
    project_dir = config.GENERATED_DIR / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)
    project_dir.mkdir(parents=True, exist_ok=True)

    for generated_file in server.files:
        dest = project_dir / Path(generated_file.path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(generated_file.content, encoding="utf-8")

    return project_dir


def build_zip(project_id: str) -> Path:
    project_dir = config.GENERATED_DIR / project_id
    if not project_dir.exists():
        raise FileNotFoundError(f"No generated files on disk for project '{project_id}'")

    config.GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = config.GENERATED_DIR / f"{project_id}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, arcname=file_path.relative_to(project_dir).as_posix())

    return zip_path
