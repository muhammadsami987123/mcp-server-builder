"""Page routes for serving HTML templates."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import TEMPLATES_DIR

router = APIRouter()

# Setup Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_template(template_name: str, **context):
    """Render a Jinja2 template."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)


@router.get("/", response_class=HTMLResponse)
async def home():
    """Home page."""
    return render_template("index.html", title="MCP Server Builder")


@router.get("/builder", response_class=HTMLResponse)
async def builder():
    """Builder page."""
    return render_template("builder.html", title="API Builder")


@router.get("/history", response_class=HTMLResponse)
async def history():
    """History page."""
    return render_template("history.html", title="Project History")


@router.get("/project/{project_id}", response_class=HTMLResponse)
async def project_view(project_id: str):
    """Project result page."""
    return render_template(
        "project.html",
        title="Project Results",
        project_id=project_id,
    )


@router.get("/docs/api", response_class=HTMLResponse)
async def api_docs():
    """API documentation page."""
    return render_template("docs.html", title="API Documentation")
