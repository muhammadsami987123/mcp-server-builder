"""Download and single-file content routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services import project_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/project/{project_id}/download")
async def download_project(project_id: str):
    project = project_store.load_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.generated:
        raise HTTPException(status_code=400, detail="Project has not been generated yet.")

    try:
        zip_path = project_store.build_zip(project_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("build_zip failed for project %s", project_id)
        raise HTTPException(status_code=502, detail="Failed to build the download archive.") from exc

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"{project_id}.zip",
    )


@router.get("/project/{project_id}/file")
async def get_project_file(project_id: str, path: str = Query(...)):
    project = project_store.load_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    files = (project.generated or {}).get("files", [])
    for file_entry in files:
        if file_entry.get("path") == path:
            return {"path": path, "content": file_entry.get("content", "")}

    raise HTTPException(status_code=404, detail="File not found")
