"""FastAPI application for MCP Server Builder."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import TEMPLATES_DIR, STATIC_DIR
from app.routes import pages, analysis, generation, projects, downloads

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting MCP Server Builder")
    yield
    logger.info("Shutting down MCP Server Builder")


# Create FastAPI app
app = FastAPI(
    title="MCP Server Builder",
    description="AI-powered tool to transform REST APIs into MCP servers",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pages.router, tags=["Pages"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(generation.router, prefix="/api", tags=["Generation"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(downloads.router, prefix="/api", tags=["Downloads"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

logger.info("MCP Server Builder initialized")
