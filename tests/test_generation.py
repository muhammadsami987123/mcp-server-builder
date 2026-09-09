"""Tests for app.services.mcp_generator.generate_server against the demo
API + hand-written demo design (no OpenAI call required)."""

from __future__ import annotations

import ast

import pytest

from app import config
from app.models.mcp import GenerationPreferences
from app.services import mcp_designer, mcp_generator


@pytest.fixture
def demo_api_design(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    return mcp_designer.build_demo_design()


class TestGenerateServerStructure:
    def test_produces_all_required_files(self, demo_api_design):
        api, design = demo_api_design
        server = mcp_generator.generate_server(api, design)
        paths = {f.path for f in server.files}

        required = {
            "src/server.py",
            "src/config.py",
            "src/client.py",
            "src/models.py",
            "src/tools/__init__.py",
            ".env.example",
            ".gitignore",
            "requirements.txt",
            "pyproject.toml",
            "mcp-config.json",
        }
        missing = required - paths
        assert not missing, f"generated project is missing files: {missing}"

    def test_all_python_files_are_syntactically_valid(self, demo_api_design):
        api, design = demo_api_design
        server = mcp_generator.generate_server(api, design)

        py_files = [f for f in server.files if f.path.endswith(".py")]
        assert py_files, "expected at least one generated .py file"
        for f in py_files:
            ast.parse(f.content, filename=f.path)

    def test_tool_count_matches_design(self, demo_api_design):
        api, design = demo_api_design
        server = mcp_generator.generate_server(api, design)
        assert server.tool_count == len(design.tools)


class TestGenerationPreferences:
    def test_exclude_destructive_tools_omits_delete_tools(self, demo_api_design):
        api, design = demo_api_design
        prefs = GenerationPreferences(include_read_only=True, include_destructive=False)
        server = mcp_generator.generate_server(api, design, prefs)

        combined = "\n".join(f.content for f in server.files)
        assert "delete_task" not in combined
        assert "delete_project" not in combined

    def test_include_destructive_true_includes_delete_tools(self, demo_api_design):
        api, design = demo_api_design
        prefs = GenerationPreferences(include_read_only=True, include_destructive=True)
        server = mcp_generator.generate_server(api, design, prefs)

        combined = "\n".join(f.content for f in server.files)
        assert "delete_task" in combined

    def test_generate_tests_false_omits_test_files(self, demo_api_design):
        api, design = demo_api_design
        prefs = GenerationPreferences(generate_tests=False)
        server = mcp_generator.generate_server(api, design, prefs)
        paths = {f.path for f in server.files}
        assert "tests/test_client.py" not in paths
        assert "tests/test_tools.py" not in paths


class TestRenderHelpers:
    def test_render_mcp_client_config_returns_usable_string(self, demo_api_design):
        api, design = demo_api_design
        config_str = mcp_generator.render_mcp_client_config(design)
        assert isinstance(config_str, str)
        assert len(config_str) > 0

    def test_render_readme_references_actual_tools(self, demo_api_design):
        api, design = demo_api_design
        server = mcp_generator.generate_server(api, design)
        readme = mcp_generator.render_readme(api, design, server.files)
        assert isinstance(readme, str)
        assert any(tool.name in readme for tool in design.tools)
