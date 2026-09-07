"""MCP server generation routes."""
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.models.api import APIRepresentation
from app.models.mcp import MCPServerDesign
from app.services.openai_service import OpenAIService
from app.services.mcp_generator import MCPServerGenerator
from app.services.validator import MCPServerValidator
from app.services.project_manager import ProjectManager

logger = logging.getLogger(__name__)

router = APIRouter()


class DesignToolsRequest(BaseModel):
    """Request to design MCP tools."""
    api: dict  # APIRepresentation as dict
    max_tools: int = 10
    custom_name: Optional[str] = None


class DesignToolsResponse(BaseModel):
    """Response with designed tools."""
    success: bool
    design: Optional[dict] = None
    tool_count: int = 0
    errors: list = []


class GenerateServerRequest(BaseModel):
    """Request to generate MCP server."""
    design: dict  # MCPServerDesign as dict
    validate: bool = True


class GenerateServerResponse(BaseModel):
    """Response with generated server files."""
    success: bool
    project_id: Optional[str] = None
    files_count: int = 0
    file_tree: dict = {}
    validation: dict = {}
    errors: list = []
    warnings: list = []


@router.post("/design-tools", response_model=DesignToolsResponse)
async def design_tools(request: DesignToolsRequest):
    """
    Design MCP tools from API using AI.

    Endpoint: POST /api/design-tools
    Request:
        {
            "api": { APIRepresentation },
            "max_tools": 10,
            "custom_name": "my_api_mcp"
        }

    Response:
        {
            "success": bool,
            "design": { MCPServerDesign },
            "tool_count": 5,
            "errors": []
        }
    """
    try:
        # Reconstruct APIRepresentation from dict
        api_dict = request.api
        api = APIRepresentation(**api_dict)

        logger.info(f"Designing tools for {api.name}")

        # Initialize OpenAI service
        try:
            openai_service = OpenAIService()
        except ValueError as e:
            logger.error(f"OpenAI not configured: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="OpenAI service not configured. Set OPENAI_API_KEY environment variable.",
            )

        # Design tools
        success, design, errors = await openai_service.design_tools(api, request.max_tools)

        if not success:
            return DesignToolsResponse(
                success=False,
                tool_count=0,
                errors=errors,
            )

        # Apply custom name if provided
        if request.custom_name:
            design.server_name = request.custom_name

        return DesignToolsResponse(
            success=True,
            design=design.dict(),
            tool_count=len(design.tools),
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tool design error: {str(e)}")
        raise HTTPException(status_code=500, detail="Tool design failed")


@router.post("/generate", response_model=GenerateServerResponse)
async def generate_server(
    request: GenerateServerRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generate complete MCP server code.

    Endpoint: POST /api/generate
    Request:
        {
            "design": { MCPServerDesign },
            "validate": true
        }

    Response:
        {
            "success": bool,
            "project_id": "uuid-here",
            "files_count": 12,
            "file_tree": { ... },
            "validation": { ... },
            "errors": []
        }
    """
    try:
        # Reconstruct design from dict
        design = MCPServerDesign(**request.design)

        logger.info(f"Generating MCP server: {design.server_name}")

        # Generate project files
        generator = MCPServerGenerator()
        files = generator.generate_project(design)

        logger.info(f"Generated {len(files)} files")

        # Validate if requested
        validation_result = None
        if request.validate:
            validator = MCPServerValidator()
            validation_result = validator.validate_project(files, design)
            logger.info(f"Validation: {validation_result.to_dict()}")

            if validation_result.to_dict()["error_count"] > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Generated server validation failed",
                )

        # Create file tree
        file_tree = ProjectManager.get_file_tree(files)

        # Store project (asynchronous)
        project_id = str(__import__("uuid").uuid4())
        background_tasks.add_task(
            _store_project,
            project_id,
            design,
            files,
            validation_result,
        )

        return GenerateServerResponse(
            success=True,
            project_id=project_id,
            files_count=len(files),
            file_tree=file_tree,
            validation=validation_result.to_dict() if validation_result else {},
            errors=[],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Code generation failed")


async def _store_project(project_id: str, design, files: dict, validation_result):
    """Store project files asynchronously."""
    try:
        from app.services.project_manager import ProjectManager
        from app.config import DATA_DIR

        # Save project metadata
        metadata = {
            "project_id": project_id,
            "server_name": design.server_name,
            "server_description": design.server_description,
            "source_api_name": design.source_api_name,
            "api_base_url": design.api_base_url,
            "tool_count": len(design.tools),
            "files_count": len(files),
            "created_at": __import__("datetime").datetime.utcnow().isoformat(),
            "validation": validation_result.to_dict() if validation_result else {},
        }

        # Save to JSON
        import json
        project_file = DATA_DIR / f"{project_id}.json"
        project_file.write_text(json.dumps(metadata, indent=2))

        logger.info(f"Project stored: {project_id}")
    except Exception as e:
        logger.error(f"Error storing project: {str(e)}")
