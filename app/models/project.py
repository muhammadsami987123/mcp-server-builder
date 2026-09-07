"""Project storage and history models."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectMetadata(BaseModel):
    """Project metadata for listing and history."""
    project_id: str
    name: str
    description: str
    source_url: str
    source_api_name: str
    created_at: str  # ISO format
    status: str  # "completed", "error", "in_progress"
    error_message: Optional[str] = None
    tool_count: int = 0


class ProjectSummary(BaseModel):
    """Minimal project summary for list view."""
    project_id: str
    name: str
    source_api_name: str
    created_at: str
    status: str
    tool_count: int = 0


class HistoryResponse(BaseModel):
    """Response for history listing."""
    projects: List[ProjectSummary]
    total_count: int
    limit: int
    offset: int
