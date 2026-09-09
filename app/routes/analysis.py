"""Discovery, analysis, and AI tool-design routes.

The full pipeline is synchronous per-call and stateless between requests: every
step loads the project from project_store, mutates it, and saves it back.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import config
from app.models.api import APIRepresentation, DiscoveryResult, SpecType
from app.models.mcp import MCPProject
from app.services import project_store
from app.services.api_analyzer import normalize_api
from app.services.api_discovery import discover_api
from app.services.mcp_designer import build_demo_design, design_tools
from app.services.openai_service import OpenAIServiceError
from app.services.url_fetcher import SSRFError, validate_url_format

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class DiscoverRequest(BaseModel):
    url: str
    demo: bool = False


class AnalyzeRequest(BaseModel):
    project_id: str


class DesignToolsRequest(BaseModel):
    project_id: str
    demo: bool = False


def _touch(project: MCPProject) -> None:
    project.updated_at = datetime.now(timezone.utc)


def _fail(project: MCPProject, exc: Exception) -> None:
    project.status = "failed"
    project.error_message = str(exc)
    _touch(project)
    project_store.save_project(project)


def _cache(project: MCPProject, key: str, value: dict) -> None:
    # project.preferences is the only generic bucket on MCPProject; namespace
    # internal pipeline state under keys the frontend never sends back so a
    # later GenerationPreferences merge can't clobber it.
    prefs = dict(project.preferences or {})
    prefs[key] = value
    project.preferences = prefs


@router.post("/discover")
async def discover(payload: DiscoverRequest):
    if payload.demo:
        project = project_store.create_project(payload.url or "demo://task-manager")
        project.status = "discovering"
        project_store.save_project(project)
        try:
            raw_spec = json.loads(config.DEMO_SPEC_PATH.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - fixture read must never crash the request
            logger.exception("Failed to load demo spec for project %s", project.id)
            _fail(project, exc)
            raise HTTPException(status_code=502, detail="Failed to load the demo API specification.") from exc
        result = DiscoveryResult(
            source_url=project.source_url,
            spec_type=SpecType.OPENAPI,
            spec_format="json",
            raw_spec=raw_spec,
            discovered_pages=[],
            success=True,
        )
    else:
        ok, reason = validate_url_format(payload.url)
        if not ok:
            raise HTTPException(status_code=400, detail=reason or "Invalid URL")

        project = project_store.create_project(payload.url)
        project.status = "discovering"
        project_store.save_project(project)

        try:
            result = await discover_api(payload.url)
        except SSRFError as exc:
            _fail(project, exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - any discovery failure must become a clean 502
            logger.exception("discover_api failed for project %s", project.id)
            _fail(project, exc)
            raise HTTPException(
                status_code=502, detail="Failed to discover the API from the given URL."
            ) from exc

        if not result.success:
            project.status = "failed"
            project.error_message = result.error_message or "No API specification could be discovered."
            _touch(project)
            project_store.save_project(project)
            raise HTTPException(status_code=400, detail=project.error_message)

    project.status = "discovering"
    _cache(project, "discovery", result.model_dump(mode="json"))
    _touch(project)
    project_store.save_project(project)

    return {"project_id": project.id, "discovery": result.model_dump(mode="json")}


@router.post("/analyze")
async def analyze(payload: AnalyzeRequest):
    project = project_store.load_project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    discovery_data = (project.preferences or {}).get("discovery")
    if not discovery_data:
        raise HTTPException(status_code=400, detail="Project has no discovery data. Run /api/discover first.")

    try:
        discovery = DiscoveryResult.model_validate(discovery_data)
        api = normalize_api(discovery)
    except ValueError as exc:
        _fail(project, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("normalize_api failed for project %s", project.id)
        _fail(project, exc)
        raise HTTPException(status_code=502, detail="Failed to analyze the discovered API.") from exc

    project.api = api.model_dump(mode="json")
    project.status = "analyzing"
    _touch(project)
    project_store.save_project(project)

    return {"api": api.model_dump(mode="json")}


@router.post("/design-tools")
async def design_tools_route(payload: DesignToolsRequest):
    project = project_store.load_project(payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        if payload.demo:
            api, design = build_demo_design()
        else:
            if not project.api:
                raise ValueError("Project has no analyzed API. Run /api/analyze first.")
            api = APIRepresentation.model_validate(project.api)
            design = await design_tools(api)
    except ValueError as exc:
        _fail(project, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenAIServiceError as exc:
        _fail(project, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("design_tools failed for project %s", project.id)
        _fail(project, exc)
        raise HTTPException(status_code=502, detail="Failed to design MCP tools.") from exc

    project.api = api.model_dump(mode="json")
    project.design = design.model_dump(mode="json")
    project.status = "designing"
    _touch(project)
    project_store.save_project(project)

    return {"design": design.model_dump(mode="json")}
