"""Tests for app.services.mcp_designer. openai_service.call_structured is
always monkeypatched — these tests never call the real OpenAI API."""

from __future__ import annotations

import pytest

from app import config
from app.models.mcp import MCPServerDesign
from app.services import mcp_designer, openai_service
from app.services.openapi_parser import parse_openapi


@pytest.fixture
def demo_api(demo_spec):
    return parse_openapi(demo_spec, "https://api.demo-taskmanager.dev/v1")


class TestDesignToolsCrossValidation:
    async def test_drops_hallucinated_tool_and_records_it_as_ignored(
        self, monkeypatch, demo_api
    ):
        ai_response = mcp_designer._AIDesignResponse(
            server_name="task-manager-mcp",
            description="MCP server for the Task Manager API",
            tools=[
                mcp_designer._AIToolSpec(
                    name="list_tasks",
                    description="List tasks",
                    method="GET",
                    path="/tasks",
                    parameters=[],
                    group="tasks",
                ),
                mcp_designer._AIToolSpec(
                    name="teleport_task",
                    description="Hallucinated tool with no matching endpoint",
                    method="POST",
                    path="/tasks/{id}/teleport",
                    parameters=[],
                    group="tasks",
                ),
            ],
            ignored_endpoints=[],
            reasoning="test fixture",
        )

        async def fake_call_structured(system_prompt, user_prompt, response_model, *, retries=2):
            return ai_response

        monkeypatch.setattr(openai_service, "call_structured", fake_call_structured)

        design = await mcp_designer.design_tools(demo_api)

        tool_names = {t.name for t in design.tools}
        assert "list_tasks" in tool_names
        assert "teleport_task" not in tool_names
        assert any("teleport" in entry.lower() for entry in design.ignored_endpoints)

    async def test_kept_tool_copies_destructive_flag_from_matched_endpoint(
        self, monkeypatch, demo_api
    ):
        ai_response = mcp_designer._AIDesignResponse(
            server_name="task-manager-mcp",
            description="MCP server for the Task Manager API",
            tools=[
                mcp_designer._AIToolSpec(
                    name="delete_task",
                    description="Delete a task",
                    method="DELETE",
                    path="/tasks/{id}",
                    parameters=[],
                    group="tasks",
                ),
            ],
            ignored_endpoints=[],
            reasoning="test fixture",
        )

        async def fake_call_structured(system_prompt, user_prompt, response_model, *, retries=2):
            return ai_response

        monkeypatch.setattr(openai_service, "call_structured", fake_call_structured)

        design = await mcp_designer.design_tools(demo_api)

        assert len(design.tools) == 1
        assert design.tools[0].destructive is True


class TestDesignToolsErrorPropagation:
    async def test_raises_openai_service_error_after_exhausted_retries(
        self, monkeypatch, demo_api
    ):
        async def fake_call_structured(system_prompt, user_prompt, response_model, *, retries=2):
            raise openai_service.OpenAIServiceError(
                "OpenAI failed to produce a valid structured response after 3 attempt(s)"
            )

        monkeypatch.setattr(openai_service, "call_structured", fake_call_structured)

        with pytest.raises(openai_service.OpenAIServiceError):
            await mcp_designer.design_tools(demo_api)


class TestBuildDemoDesign:
    def test_works_without_openai_api_key(self, monkeypatch):
        monkeypatch.setattr(config, "OPENAI_API_KEY", "")

        api, design = mcp_designer.build_demo_design()

        assert len(api.endpoints) == 8
        assert isinstance(design, MCPServerDesign)
        assert len(design.tools) == 8

        # Every hand-written demo tool must trace back to a real endpoint.
        endpoint_pairs = {(e.method.value, e.path) for e in api.endpoints}
        for tool in design.tools:
            assert (tool.method.value, tool.path) in endpoint_pairs

        destructive_names = {t.name for t in design.tools if t.destructive}
        assert len(destructive_names) >= 2
