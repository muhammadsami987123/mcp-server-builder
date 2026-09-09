"""FastAPI application entrypoint: middleware, templates, routers, error handling."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from app.routes import analysis, downloads, generation, pages, projects

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Server Builder")

if config.CORS_ORIGINS.strip() == "*":
    # Wildcard origins and credentialed CORS are mutually exclusive per spec.
    cors_kwargs = {"allow_origins": ["*"], "allow_credentials": False}
else:
    origins = [origin.strip() for origin in config.CORS_ORIGINS.split(",") if origin.strip()]
    cors_kwargs = {"allow_origins": origins, "allow_credentials": True}

app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_headers=["*"],
    **cors_kwargs,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.state.templates = Jinja2Templates(directory="app/templates")

app.include_router(pages.router)
app.include_router(analysis.router)
app.include_router(generation.router)
app.include_router(projects.router)
app.include_router(downloads.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # FastAPI's built-in HTTPException handler runs first for routes that raise
    # HTTPException directly, so only genuinely unexpected errors land here.
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal error"})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/robots.txt")
async def robots_txt() -> FileResponse:
    return FileResponse("app/static/robots.txt", media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap_xml() -> FileResponse:
    return FileResponse("app/static/sitemap.xml", media_type="application/xml")
