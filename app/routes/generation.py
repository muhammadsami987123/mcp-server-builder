"""Server generation, validation, and regeneration routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.api import APIRepresentation
from app.models.mcp import GeneratedMCPServer, GenerationPreferences, MCPProject, MCPServerDesign, ValidationResult
from app.services import project_store
from app.services.mcp_generator import generate_server
from app.services.validator import validate_generated_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class GenerateRequest(BaseModel):
    project_id: str
    preferences: Optional[GenerationPreferences] = None


class RegenerateRequest(BaseModel):
    project_id: str
    preferences: GenerationPreferences


class ValidateRequest(BaseModel):
    project_id: str


def _touch(project: MCPProject) -> None:
    project.updated_at = datetime.now(timezone.utc)


def _fail(project: MCPProject, exc: Exception) -> None:
    project.status = "failed"
    project.error_message = str(exc)
    _touch(project)
    project_store.save_project(project)


def _merge_preferences(project: MCPProject, preferences: Optional[GenerationPreferences]) -> None:
    if preferences is None:
        return
    merged = dict(project.preferences or {})
    merged.update(preferences.model_dump(mode="json"))
    project.preferences = merged


def _run_generation(
    project: MCPProject, preferences: Optional[GenerationPreferences]
) -> tuple[GeneratedMCPServer, ValidationResult]:
    if not project.api or not project.design:
        raise ValueError("Project must be analyzed and designed before generation.")

    api = APIRepresentation.model_validate(project.api)
    design = MCPServerDesign.model_validate(project.design)

    project.status = "generating"
    _touch(project)
    project_store.save_project(project)

    server = generate_server(api, design, preferences)
    project_store.save_generated_files_to_disk(project.id, server)

    project.status = "validating"
    _touch(project)
    project_store.save_project(project)

    validation = validate_generated_server(server)

    project.generated = server.model_dump(mode="json")
    project.validation = validation.model_dump(mode="json")
    _merge_preferences(project, preferences)

    if validation.passed:
        project.status = "ready"
        project.error_message = None
    else:
        project.status = "failed"
        project.error_message = "; ".join(validation.errors) or "Generated server failed validation."

    _touch(project)
    project_store.save_project(project)
    return server, validation


def _generated_response(server: GeneratedMCPServer, validation: ValidationResult) -> dict:
    return {
        "generated": {
            "server_name": server.server_name,
            "tool_count": server.tool_count,
            "files": [f.path for f in server.files],
        },
        "validation": validation.model_dump(mode="json"),
    }


@router.post("/generate")
async def generate(payload: GenerateRequest):
    project = project_store.load_project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        server, validation = _run_generation(project, payload.preferences)
    except ValueError as exc:
        _fail(project, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("generate_server failed for project %s", project.id)
        _fail(project, exc)
        raise HTTPException(status_code=502, detail="Failed to generate the MCP server.") from exc

    return _generated_response(server, validation)


@router.post("/regenerate")
async def regenerate(payload: RegenerateRequest):
    project = project_store.load_project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        server, validation = _run_generation(project, payload.preferences)
    except ValueError as exc:
        _fail(project, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("regenerate failed for project %s", project.id)
        _fail(project, exc)
        raise HTTPException(status_code=502, detail="Failed to regenerate the MCP server.") from exc

    return _generated_response(server, validation)


@router.post("/validate")
async def validate(payload: ValidateRequest):
    project = project_store.load_project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.generated:
        raise HTTPException(status_code=400, detail="Project has not been generated yet.")

    try:
        server = GeneratedMCPServer.model_validate(project.generated)
        project.status = "validating"
        _touch(project)
        project_store.save_project(project)
        validation = validate_generated_server(server)
    except Exception as exc:  # noqa: BLE001
        logger.exception("validate_generated_server failed for project %s", project.id)
        _fail(project, exc)
        raise HTTPException(status_code=502, detail="Failed to validate the generated server.") from exc

    project.validation = validation.model_dump(mode="json")
    project.status = "ready" if validation.passed else "failed"
    if not validation.passed:
        project.error_message = "; ".join(validation.errors) or "Generated server failed validation."
    _touch(project)
    project_store.save_project(project)

    return {"validation": validation.model_dump(mode="json")}
