"""Server-rendered page routes (marketing home, builder, history, project detail)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.services import project_store

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return request.app.state.templates.TemplateResponse("index.html", {"request": request})


@router.get("/builder", response_class=HTMLResponse)
async def builder(request: Request):
    return request.app.state.templates.TemplateResponse("builder.html", {"request": request})


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    return request.app.state.templates.TemplateResponse("history.html", {"request": request})


@router.get("/project/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: str):
    project = project_store.load_project(project_id)
    if project is None:
        return request.app.state.templates.TemplateResponse(
            "project.html",
            {"request": request, "project_id": project_id, "not_found": True},
            status_code=404,
        )
    return request.app.state.templates.TemplateResponse(
        "project.html",
        {"request": request, "project_id": project_id, "not_found": False},
    )
