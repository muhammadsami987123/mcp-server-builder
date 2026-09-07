"""API analysis and discovery routes."""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.api import DiscoveryResult, APIRepresentation
from app.services.api_discovery import APIDiscovery
from app.services.api_analyzer import APIAnalyzer
from app.services.url_fetcher import SSRFException

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """API analyze request."""
    url: str


class AnalyzeResponse(BaseModel):
    """API analyze response."""
    success: bool
    api: dict = None
    analysis: dict = None
    errors: list = []
    warnings: list = []


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_api(request: AnalyzeRequest):
    """
    Analyze and discover API from URL.

    Endpoint: POST /api/analyze
    Request:
        {
            "url": "https://api.example.com"
        }

    Response:
        {
            "success": bool,
            "api": { APIRepresentation },
            "analysis": { analysis results },
            "errors": [],
            "warnings": []
        }
    """
    try:
        url = request.url.strip()

        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

        # Discover API
        logger.info(f"Discovering API from {url}")
        discovery_result = await APIDiscovery.discover(url)

        if not discovery_result.success:
            return AnalyzeResponse(
                success=False,
                errors=discovery_result.errors,
                warnings=discovery_result.warnings,
            )

        # Analyze discovered API
        analysis = APIAnalyzer.analyze(discovery_result.api)

        return AnalyzeResponse(
            success=True,
            api=discovery_result.api.dict(),
            analysis=analysis,
            errors=discovery_result.errors,
            warnings=discovery_result.warnings,
        )

    except SSRFException as e:
        logger.warning(f"SSRF protection triggered: {str(e)}")
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Analysis failed")


@router.get("/endpoints/{project_id}")
async def get_endpoints(project_id: str, method: str = None, tag: str = None):
    """
    Get endpoints for a project.

    Endpoint: GET /api/endpoints/{project_id}
    Query params:
        - method: Filter by HTTP method (GET, POST, etc.)
        - tag: Filter by tag

    Response:
        {
            "endpoints": [
                {
                    "path": "/users/{id}",
                    "method": "GET",
                    "summary": "Get user by ID",
                    "parameters_count": 1,
                    "requires_body": false
                }
            ],
            "total": 5
        }
    """
    try:
        # This would load the project and return its endpoints
        # For now, return a placeholder
        return {
            "endpoints": [],
            "total": 0,
            "project_id": project_id,
        }
    except Exception as e:
        logger.error(f"Error fetching endpoints: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch endpoints")
