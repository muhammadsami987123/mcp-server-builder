"""Project management routes."""
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import DATA_DIR
from app.models.project import ProjectSummary, HistoryResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/project/{project_id}")
async def get_project(project_id: str):
    """
    Get project details.

    Endpoint: GET /api/project/{project_id}
    Response:
        {
            "project_id": "uuid",
            "server_name": "my_api_mcp",
            "server_description": "MCP server for My API",
            "source_api_name": "My API",
            "api_base_url": "https://api.example.com",
            "tool_count": 5,
            "files_count": 12,
            "created_at": "2024-09-07T...",
            "status": "completed"
        }
    """
    try:
        project_file = DATA_DIR / f"{project_id}.json"

        if not project_file.exists():
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        project_data = json.loads(project_file.read_text())
        return project_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch project")


@router.get("/project/{project_id}/tools")
async def get_project_tools(project_id: str):
    """
    Get MCP tools for a project.

    Endpoint: GET /api/project/{project_id}/tools
    Response:
        {
            "tools": [
                {
                    "name": "get_user",
                    "description": "Retrieve user by ID",
                    "method": "GET",
                    "path": "/users/{id}",
                    "input_schema": { ... }
                }
            ],
            "total": 5
        }
    """
    try:
        project_file = DATA_DIR / f"{project_id}.json"

        if not project_file.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        project_data = json.loads(project_file.read_text())

        # Return tools from design
        return {
            "tools": project_data.get("tools", []),
            "total": len(project_data.get("tools", [])),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project tools: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch tools")


@router.get("/project/{project_id}/files")
async def get_project_files(project_id: str):
    """
    Get file tree for a project.

    Endpoint: GET /api/project/{project_id}/files
    Response:
        {
            "files": {
                "src": {
                    "server.py": { "type": "file", "size": 1234 },
                    "config.py": { "type": "file", "size": 567 }
                },
                "README.md": { "type": "file", "size": 2345 }
            },
            "total_files": 12
        }
    """
    try:
        project_file = DATA_DIR / f"{project_id}.json"

        if not project_file.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        project_data = json.loads(project_file.read_text())

        return {
            "files": project_data.get("files", {}),
            "total_files": project_data.get("files_count", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project files: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch files")


@router.get("/projects")
async def list_projects(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all projects (history).

    Endpoint: GET /api/projects
    Query params:
        - limit: Maximum number of projects (default: 20, max: 100)
        - offset: Skip first N projects (default: 0)

    Response:
        {
            "projects": [
                {
                    "project_id": "uuid",
                    "name": "my_api_mcp",
                    "source_api_name": "My API",
                    "created_at": "2024-09-07T...",
                    "status": "completed",
                    "tool_count": 5
                }
            ],
            "total_count": 42,
            "limit": 20,
            "offset": 0
        }
    """
    try:
        # List all project files
        project_files = sorted(
            DATA_DIR.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        total_count = len(project_files)

        # Apply pagination
        paginated_files = project_files[offset : offset + limit]

        projects = []
        for project_file in paginated_files:
            try:
                data = json.loads(project_file.read_text())
                project = ProjectSummary(
                    project_id=data.get("project_id", ""),
                    name=data.get("server_name", ""),
                    source_api_name=data.get("source_api_name", ""),
                    created_at=data.get("created_at", ""),
                    status=data.get("status", "completed"),
                    tool_count=data.get("tool_count", 0),
                )
                projects.append(project)
            except Exception as e:
                logger.warning(f"Error loading project {project_file}: {str(e)}")

        return HistoryResponse(
            projects=projects,
            total_count=total_count,
            limit=limit,
            offset=offset,
        ).dict()

    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list projects")


@router.post("/project/{project_id}/regenerate")
async def regenerate_project(
    project_id: str,
    custom_settings: Optional[dict] = None,
):
    """
    Regenerate a project with custom settings.

    Endpoint: POST /api/project/{project_id}/regenerate
    Request:
        {
            "max_tools": 15,
            "custom_name": "new_server_name"
        }

    Response:
        {
            "success": bool,
            "new_project_id": "uuid",
            "changes": { ... }
        }
    """
    try:
        project_file = DATA_DIR / f"{project_id}.json"

        if not project_file.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        # Load original project
        project_data = json.loads(project_file.read_text())

        # For now, return a placeholder
        return {
            "success": True,
            "new_project_id": project_id,
            "changes": {},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to regenerate project")
