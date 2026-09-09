"""Tests for app.services.validator.validate_generated_server."""

from __future__ import annotations

import copy

from app.models.mcp import GeneratedFile, GeneratedMCPServer
from app.services.validator import validate_generated_server


def _valid_server() -> GeneratedMCPServer:
    files = [
        GeneratedFile(
            path="src/server.py",
            content=(
                "from mcp.server.fastmcp import FastMCP\n\n"
                "mcp = FastMCP('demo-mcp')\n\n"
                "@mcp.tool()\n"
                "def list_tasks() -> dict:\n"
                "    \"\"\"List tasks.\"\"\"\n"
                "    return {}\n"
            ),
        ),
        GeneratedFile(
            path="src/config.py",
            content=(
                "import os\n\n"
                "API_BASE_URL = os.environ.get('API_BASE_URL', '')\n"
                "API_KEY = os.environ.get('API_KEY', '')\n"
            ),
        ),
        GeneratedFile(
            path="src/client.py",
            content="import httpx\n\nclient = httpx.AsyncClient()\n",
        ),
        GeneratedFile(
            path="src/models.py",
            content="from pydantic import BaseModel\n\n\nclass ListTasksInput(BaseModel):\n    pass\n",
        ),
        GeneratedFile(path="src/tools/__init__.py", content=""),
        GeneratedFile(path=".env.example", content="API_BASE_URL=\nAPI_KEY=\n"),
        GeneratedFile(
            path="requirements.txt",
            content="mcp\nhttpx\npydantic\npython-dotenv\n",
        ),
    ]
    return GeneratedMCPServer(files=files, server_name="demo-mcp", tool_count=1)


class TestValidateGeneratedServer:
    def test_valid_server_passes(self):
        server = _valid_server()
        result = validate_generated_server(server)

        failing_errors = [c for c in result.checks if c.severity == "error" and not c.passed]
        assert not failing_errors, f"unexpected failing error checks: {failing_errors}"
        assert result.passed is True

    def test_injected_syntax_error_is_caught(self):
        server = copy.deepcopy(_valid_server())
        for f in server.files:
            if f.path == "src/server.py":
                f.content = "def broken(:\n    pass\n"  # deliberately invalid syntax

        result = validate_generated_server(server)

        assert result.passed is False
        failing_errors = [c for c in result.checks if c.severity == "error" and not c.passed]
        assert failing_errors, "expected at least one failing error-severity check"
        assert any(
            "src/server.py" in c.message or "src/server.py" in c.name for c in failing_errors
        )
