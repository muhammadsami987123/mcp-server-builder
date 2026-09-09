"""Project inspection, history listing, deletion, and feedback routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.project import HistoryResponse, ProjectSummary
from app.services import project_store

router = APIRouter(prefix="/api")


class FeedbackRequest(BaseModel):
    rating: int
    comment: str = ""


@router.get("/project/{project_id}")
async def get_project(project_id: str):
    project = project_store.load_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.model_dump(mode="json")


@router.get("/project/{project_id}/files")
async def get_project_files(project_id: str):
    project = project_store.load_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    files = (project.generated or {}).get("files", [])
    return {"files": files}


@router.get("/project/{project_id}/tools")
async def get_project_tools(project_id: str):
    project = project_store.load_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    tools = (project.design or {}).get("tools", [])
    return {"tools": tools}


@router.get("/history")
async def history():
    metadata = project_store.list_projects()
    summaries = [
        ProjectSummary(
            id=m.id,
            server_name=m.server_name,
            tool_count=m.tool_count,
            created_at=m.created_at,
            status=m.status,
        )
        for m in metadata
    ]
    response = HistoryResponse(projects=summaries, total=len(summaries))
    return response.model_dump(mode="json")


@router.delete("/project/{project_id}")
async def delete_project_route(project_id: str):
    project = project_store.load_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project_store.delete_project(project_id)
    return {"ok": True}


@router.post("/project/{project_id}/feedback")
async def submit_feedback(project_id: str, payload: FeedbackRequest):
    project = project_store.load_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Feedback is sibling data, not part of the MCPProject model — kept inside
    # the generic preferences bucket so project_store's model contract is untouched.
    prefs = dict(project.preferences or {})
    feedback_list = list(prefs.get("feedback", []))
    feedback_list.append(
        {
            "rating": payload.rating,
            "comment": payload.comment,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    prefs["feedback"] = feedback_list
    project.preferences = prefs
    project.updated_at = datetime.now(timezone.utc)
    project_store.save_project(project)

    return {"ok": True}
