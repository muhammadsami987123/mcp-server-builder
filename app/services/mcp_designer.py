"""AI-driven MCP tool design, with mandatory cross-validation against real endpoints."""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel

from app import config
from app.models.api import APIRepresentation, AuthType, Endpoint
from app.models.mcp import MCPParameter, MCPServerDesign, MCPTool
from app.services import openai_service
from app.services.api_analyzer import summarize_for_ai
from app.services.openapi_parser import parse_openapi

_SYSTEM_PROMPT = """You are an expert API architect designing a Model Context Protocol (MCP) \
server interface from a discovered HTTP API.

Given a compact JSON summary of an API's endpoints, design a clean, developer-friendly set of \
MCP tools. Rules:
- Do not blindly expose every raw endpoint. Merge, rename, or skip endpoints to produce a clean \
  interface (e.g. prefer `list_users` over `get_users_list_v2`).
- Every tool MUST correspond to exactly one endpoint from the provided summary, referenced by its \
  exact "method" and "path" as given. Never invent an endpoint, parameter, method, or path that is \
  not present in the summary.
- Use short, descriptive, snake_case tool names.
- Write a one-sentence description per tool explaining what it does.
- Include every parameter the endpoint actually accepts (path, query, and body fields), each with a \
  name, a JSON-schema-style type ("string" | "number" | "integer" | "boolean" | "array" | "object"), \
  a short description, and whether it is required.
- Group related tools under a short lowercase "group" name (usually the resource/tag name).
- If an endpoint is not useful as an MCP tool (e.g. redundant, purely internal, or unclear), omit it \
  from "tools" and list its "method path" string in "ignored_endpoints" instead.
- Respond with a single strict JSON object matching the required schema. No prose, no markdown.
"""


class _AIToolParam(BaseModel):
    name: str
    type: str
    description: str
    required: bool = False
    default: Any | None = None


class _AIToolSpec(BaseModel):
    name: str
    description: str
    method: str
    path: str
    parameters: list[_AIToolParam] = []
    group: str = "general"


class _AIDesignResponse(BaseModel):
    server_name: str
    description: str
    tools: list[_AIToolSpec]
    ignored_endpoints: list[str] = []
    reasoning: str = ""


def _endpoint_index(api: APIRepresentation) -> dict[tuple[str, str], Endpoint]:
    return {(endpoint.method.value, endpoint.path): endpoint for endpoint in api.endpoints}


def _build_input_schema(params: list[MCPParameter]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for param in params:
        prop: dict[str, Any] = {"type": param.type, "description": param.description}
        if param.default is not None:
            prop["default"] = param.default
        properties[param.name] = prop
        if param.required:
            required.append(param.name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _derive_auth(api: APIRepresentation) -> tuple[AuthType, Optional[str]]:
    if not api.authentication:
        return AuthType.NONE, None
    scheme = api.authentication[0]
    if scheme.header_name:
        return scheme.type, scheme.header_name
    default_headers = {
        AuthType.BEARER: "Authorization",
        AuthType.BASIC: "Authorization",
        AuthType.API_KEY: "X-API-Key",
    }
    return scheme.type, default_headers.get(scheme.type)


async def design_tools(api: APIRepresentation) -> MCPServerDesign:
    summary = summarize_for_ai(api)
    user_prompt = json.dumps(summary, ensure_ascii=False)

    result = await openai_service.call_structured(_SYSTEM_PROMPT, user_prompt, _AIDesignResponse)
    ai_response = result if isinstance(result, _AIDesignResponse) else _AIDesignResponse.model_validate(
        result.model_dump()
    )

    endpoint_index = _endpoint_index(api)
    tools: list[MCPTool] = []
    ignored_endpoints: list[str] = list(ai_response.ignored_endpoints)

    for spec in ai_response.tools:
        key = (spec.method.strip().upper(), spec.path.strip())
        endpoint = endpoint_index.get(key)
        if endpoint is None:
            # Anti-hallucination guard: never trust the model's method/path claims verbatim.
            ignored_endpoints.append(f"{key[0]} {key[1]}")
            continue

        parameters = [
            MCPParameter(
                name=param.name,
                type=param.type,
                description=param.description,
                required=param.required,
                default=param.default,
            )
            for param in spec.parameters
        ]

        tools.append(
            MCPTool(
                name=spec.name,
                description=spec.description,
                method=endpoint.method,
                path=endpoint.path,
                input_schema=_build_input_schema(parameters),
                parameters=parameters,
                source_operation_id=endpoint.operation_id,
                group=spec.group or "general",
                destructive=endpoint.destructive,
                selected=True,
            )
        )

    auth_type, auth_header_name = _derive_auth(api)

    return MCPServerDesign(
        server_name=ai_response.server_name,
        description=ai_response.description,
        tools=tools,
        base_url=api.base_url,
        auth_type=auth_type,
        auth_header_name=auth_header_name,
        ignored_endpoints=ignored_endpoints,
        reasoning=ai_response.reasoning,
    )


def _demo_tool(
    endpoint_index: dict[tuple[str, str], Endpoint],
    *,
    name: str,
    description: str,
    method: str,
    path: str,
    group: str,
    parameters: list[MCPParameter],
) -> MCPTool:
    endpoint = endpoint_index[(method, path)]
    return MCPTool(
        name=name,
        description=description,
        method=endpoint.method,
        path=endpoint.path,
        input_schema=_build_input_schema(parameters),
        parameters=parameters,
        source_operation_id=endpoint.operation_id,
        group=group,
        destructive=endpoint.destructive,
        selected=True,
    )


def build_demo_design() -> tuple[APIRepresentation, MCPServerDesign]:
    raw_spec = json.loads(config.DEMO_SPEC_PATH.read_text(encoding="utf-8"))
    source_url = raw_spec.get("servers", [{}])[0].get("url", "https://api.demo-taskmanager.dev/v1")
    api = parse_openapi(raw_spec, source_url)

    # build_demo_design() is intentionally synchronous (fixed contract signature) and
    # therefore cannot safely await the async OpenAI pipeline even when a key is
    # configured. Demo Mode always uses this deterministic, hand-written design so it
    # works identically with or without a key, and never makes a live call itself.
    endpoint_index = _endpoint_index(api)

    id_param = MCPParameter(name="id", type="string", description="The task ID.", required=True)
    project_id_param = MCPParameter(
        name="id", type="string", description="The project ID.", required=True
    )

    tools = [
        _demo_tool(
            endpoint_index,
            name="list_tasks",
            description="List tasks, optionally filtered by project or completion status.",
            method="GET",
            path="/tasks",
            group="tasks",
            parameters=[
                MCPParameter(name="project_id", type="string", description="Filter by project id."),
                MCPParameter(
                    name="completed", type="boolean", description="Filter by completion state."
                ),
            ],
        ),
        _demo_tool(
            endpoint_index,
            name="get_task",
            description="Get a single task by id.",
            method="GET",
            path="/tasks/{id}",
            group="tasks",
            parameters=[id_param],
        ),
        _demo_tool(
            endpoint_index,
            name="create_task",
            description="Create a new task.",
            method="POST",
            path="/tasks",
            group="tasks",
            parameters=[
                MCPParameter(name="title", type="string", description="Task title.", required=True),
                MCPParameter(name="project_id", type="string", description="Owning project id."),
                MCPParameter(name="due_date", type="string", description="Due date (ISO 8601)."),
            ],
        ),
        _demo_tool(
            endpoint_index,
            name="update_task",
            description="Update fields on an existing task.",
            method="PATCH",
            path="/tasks/{id}",
            group="tasks",
            parameters=[
                id_param,
                MCPParameter(name="title", type="string", description="New task title."),
                MCPParameter(name="completed", type="boolean", description="New completion state."),
            ],
        ),
        _demo_tool(
            endpoint_index,
            name="delete_task",
            description="Permanently delete a task.",
            method="DELETE",
            path="/tasks/{id}",
            group="tasks",
            parameters=[id_param],
        ),
        _demo_tool(
            endpoint_index,
            name="list_projects",
            description="List all projects.",
            method="GET",
            path="/projects",
            group="projects",
            parameters=[],
        ),
        _demo_tool(
            endpoint_index,
            name="create_project",
            description="Create a new project.",
            method="POST",
            path="/projects",
            group="projects",
            parameters=[
                MCPParameter(name="name", type="string", description="Project name.", required=True),
                MCPParameter(name="description", type="string", description="Project description."),
            ],
        ),
        _demo_tool(
            endpoint_index,
            name="delete_project",
            description="Permanently delete a project and all of its tasks.",
            method="DELETE",
            path="/projects/{id}",
            group="projects",
            parameters=[project_id_param],
        ),
    ]

    auth_type, auth_header_name = _derive_auth(api)

    design = MCPServerDesign(
        server_name="task_manager_mcp",
        description="MCP server for the Task Manager API (built-in Demo Mode fixture).",
        tools=tools,
        base_url=api.base_url,
        auth_type=auth_type,
        auth_header_name=auth_header_name,
        ignored_endpoints=[],
        reasoning="Fixed, hand-written demo design covering all 8 Task Manager API endpoints.",
    )
    return api, design
