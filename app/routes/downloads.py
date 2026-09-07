"""Download routes for generated servers."""
import json
import logging
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.config import DATA_DIR
from app.services.project_manager import ProjectManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/project/{project_id}/download")
async def download_project(project_id: str):
    """
    Download generated MCP server as ZIP.

    Endpoint: GET /api/project/{project_id}/download
    Response:
        Binary ZIP file with project structure
    """
    try:
        project_file = DATA_DIR / f"{project_id}.json"

        if not project_file.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        project_data = json.loads(project_file.read_text())

        # Reconstruct files from project data
        files = _reconstruct_files(project_data)

        # Create ZIP
        zip_buffer = ProjectManager.create_zip(files, project_data.get("server_name", "mcp_server"))

        # Return as downloadable file
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={project_data.get('server_name', 'mcp_server')}.zip"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download project")


@router.get("/project/{project_id}/file/{file_path:path}")
async def get_project_file(project_id: str, file_path: str):
    """
    Get a single file from a project.

    Endpoint: GET /api/project/{project_id}/file/{file_path}
    Response:
        File content (text or binary)
    """
    try:
        project_file = DATA_DIR / f"{project_id}.json"

        if not project_file.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        project_data = json.loads(project_file.read_text())

        # Reconstruct files
        files = _reconstruct_files(project_data)

        if file_path not in files:
            raise HTTPException(status_code=404, detail=f"File {file_path} not found")

        content = files[file_path]

        # Determine if text or binary
        if isinstance(content, str):
            return {"content": content}
        else:
            return {
                "content": content.decode("utf-8", errors="ignore")
                if isinstance(content, bytes)
                else str(content)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch file")


def _reconstruct_files(project_data: dict) -> dict:
    """
    Reconstruct file dictionary from project data.

    This is a placeholder - in a real implementation, you would
    either store the files in the project JSON (for small projects)
    or in a separate location (for large projects).
    """
    files = {}

    # Add files from project data if stored
    if "files" in project_data:
        files = project_data["files"]

    # Otherwise, generate default structure
    if not files:
        files = {
            "README.md": f"# {project_data.get('server_name', 'MCP Server')}\n\n{project_data.get('server_description', 'MCP Server')}",
            "requirements.txt": "mcp>=0.1.0\nhttpx>=0.24.0\npydantic>=2.0.0\npython-dotenv>=1.0.0\n",
            ".env.example": f"API_BASE_URL={project_data.get('api_base_url', '')}\nAPI_KEY=your_key_here\n",
        }

    return files
