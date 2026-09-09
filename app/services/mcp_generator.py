"""Renders a complete, runnable MCP server project from an MCPServerDesign.

All source-file skeletons come from Jinja2 templates in app/templates/mcp_project/.
Per-tool request-handling code (path substitution, query/body dispatch, error
handling) is assembled in Python first because its shape genuinely varies per
tool, then dropped into the templates as pre-indented text blocks -- this keeps
the templates simple while still being the single source of file structure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from app.models.api import APIRepresentation, AuthType
from app.models.mcp import GeneratedFile, GeneratedMCPServer, GenerationPreferences, MCPServerDesign, MCPTool

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "mcp_project"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)

_TYPE_MAP = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}

_QUERY_METHODS = {"GET", "DELETE", "HEAD"}


def _py_type(json_type: str) -> str:
    return _TYPE_MAP.get((json_type or "").lower(), "Any")


def _ident(name: str) -> str:
    """Sanitizes an arbitrary API param/tool name into a valid Python identifier."""
    ident = re.sub(r"\W", "_", name or "")
    if not ident or ident[0].isdigit():
        ident = f"_{ident}"
    if ident in {"class", "def", "return", "import", "from", "global", "async", "await", "None", "True", "False"}:
        ident = f"{ident}_"
    return ident


def _pascal_case(name: str) -> str:
    parts = re.split(r"[^0-9a-zA-Z]+", name or "")
    joined = "".join(p[:1].upper() + p[1:] for p in parts if p)
    return joined or "Tool"


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "mcp-server").lower()).strip("-")
    return slug or "mcp-server"


def _default_literal(value: Any) -> str:
    if value is None:
        return "None"
    return repr(value)


def _model_name(tool: MCPTool) -> str:
    return f"{_pascal_case(tool.name)}Input"


def _auth_vars_for(auth_type: AuthType) -> list[str]:
    if auth_type == AuthType.BEARER:
        return ["API_TOKEN"]
    if auth_type == AuthType.OAUTH2:
        return ["API_TOKEN"]
    if auth_type in (AuthType.API_KEY, AuthType.BASIC):
        return ["API_KEY"]
    return []


def _select_tools(tools: list[MCPTool], prefs: GenerationPreferences) -> list[MCPTool]:
    if prefs.selected_tool_names is not None:
        wanted = set(prefs.selected_tool_names)
        return [t for t in tools if t.name in wanted]

    selected: list[MCPTool] = []
    for tool in tools:
        if tool.destructive:
            if prefs.include_destructive:
                selected.append(tool)
        else:
            if prefs.include_read_only:
                selected.append(tool)
    return selected


def _group_tools(tools: list[MCPTool], group_by_resource: bool) -> dict[str, list[MCPTool]]:
    if not group_by_resource:
        return {"api": list(tools)} if tools else {}

    groups: dict[str, list[MCPTool]] = {}
    for tool in tools:
        key = _ident((tool.group or "general").lower())
        groups.setdefault(key, []).append(tool)
    return groups


def _model_block(tool: MCPTool) -> str:
    lines = [f"class {_model_name(tool)}(BaseModel):"]
    if not tool.parameters:
        lines.append("    pass")
        return "\n".join(lines)
    for param in tool.parameters:
        py_type = _py_type(param.type)
        field_name = _ident(param.name)
        if param.required:
            lines.append(f"    {field_name}: {py_type}")
        else:
            lines.append(f"    {field_name}: Optional[{py_type}] = {_default_literal(param.default)}")
    return "\n".join(lines)


def _tool_source_block(tool: MCPTool) -> str:
    func_name = _ident(tool.name)
    model_name = _model_name(tool)
    method = tool.method.value.lower()
    is_query = tool.method.value in _QUERY_METHODS

    path_params = [p for p in tool.parameters if f"{{{p.name}}}" in tool.path]
    path_param_idents = {_ident(p.name) for p in path_params}

    required_sig = [
        f"{_ident(p.name)}: {_py_type(p.type)}" for p in tool.parameters if p.required
    ]
    optional_sig = [
        f"{_ident(p.name)}: Optional[{_py_type(p.type)}] = None" for p in tool.parameters if not p.required
    ]
    signature = ", ".join(required_sig + optional_sig)

    kwargs = ", ".join(f"{_ident(p.name)}={_ident(p.name)}" for p in tool.parameters)

    exclude_literal = (
        "{" + ", ".join(f'"{ident}"' for ident in sorted(path_param_idents)) + "}"
        if path_param_idents
        else "set()"
    )

    lines: list[str] = []
    lines.append("    @mcp.tool()")
    lines.append(f"    async def {func_name}({signature}) -> dict[str, Any]:")
    description = (tool.description or f"Calls {tool.method.value} {tool.path}.").replace('"""', "'''")
    lines.append(f'        """{description}"""')
    lines.append(f"        payload = {model_name}({kwargs})")
    lines.append(f'        path = "{tool.path}"')
    for param in path_params:
        lines.append(f'        path = path.replace("{{{param.name}}}", str({_ident(param.name)}))')
    lines.append("        try:")
    lines.append("            async with get_client() as client:")
    dump = f"payload.model_dump(exclude_none=True, exclude={exclude_literal})"
    if is_query:
        lines.append(f"                response = await client.{method}(path, params={dump})")
    else:
        lines.append(f"                response = await client.{method}(path, json={dump})")
    lines.append("                response.raise_for_status()")
    lines.append("        except httpx.HTTPStatusError as exc:")
    lines.append(
        '            return {"error": "http_error", "status_code": exc.response.status_code, "message": str(exc)}'
    )
    lines.append("        except httpx.TimeoutException:")
    lines.append(f'            return {{"error": "timeout", "message": "Request to {func_name} timed out."}}')
    lines.append("        except httpx.RequestError as exc:")
    lines.append('            return {"error": "request_error", "message": str(exc)}')
    lines.append("        try:")
    lines.append("            return response.json()")
    lines.append("        except ValueError:")
    lines.append('            return {"result": response.text}')
    return "\n".join(lines)


def _auth_note(auth_type: AuthType, auth_vars: list[str]) -> str:
    if auth_type == AuthType.NONE or not auth_vars:
        return "This API does not require authentication."
    if auth_type == AuthType.OAUTH2:
        return (
            "This API uses OAuth2. OAuth2 flows require manual credential/token acquisition; "
            f"obtain an access token yourself and set it as `{auth_vars[0]}` in `.env`."
        )
    if auth_type == AuthType.BEARER:
        return f"This API uses bearer-token authentication. Set `{auth_vars[0]}` in `.env`."
    if auth_type == AuthType.BASIC:
        return f"This API uses basic authentication. Set `{auth_vars[0]}` in `.env`."
    if auth_type == AuthType.API_KEY:
        return f"This API uses an API key. Set `{auth_vars[0]}` in `.env`."
    return f"Set the following in `.env`: {', '.join(auth_vars)}."


def render_mcp_client_config(design: MCPServerDesign) -> str:
    server_key = _slug(design.server_name)
    auth_vars = _auth_vars_for(design.auth_type)
    entry: dict[str, Any] = {"command": "python", "args": ["src/server.py"]}
    if auth_vars:
        entry["env"] = {var: f"<your-{var.lower()}>" for var in auth_vars}
    config = {"mcpServers": {server_key: entry}}
    return json.dumps(config, indent=2)


def _tool_section(tool: MCPTool) -> str:
    lines = [f"### `{tool.name}`", "", f"`{tool.method.value} {tool.path}`", "", tool.description or "", ""]
    if tool.parameters:
        lines.append("**Parameters:**")
        for param in tool.parameters:
            req = "required" if param.required else "optional"
            lines.append(f"- `{param.name}` ({param.type}, {req}): {param.description}")
    else:
        lines.append("_No parameters._")
    return "\n".join(lines)


def render_readme(api: APIRepresentation, design: MCPServerDesign, files: list[GeneratedFile]) -> str:
    auth_vars = _auth_vars_for(design.auth_type)
    template = _env.get_template("readme.md.j2")
    env_example = "\n".join([f"API_BASE_URL={design.base_url}"] + [f"{v}=" for v in auth_vars])
    return template.render(
        server_name=design.server_name,
        description=design.description or f"MCP server generated from {api.name}.",
        api_name=api.name,
        base_url=design.base_url,
        env_example=env_example,
        tool_sections=[_tool_section(tool) for tool in design.tools],
        auth_note=_auth_note(design.auth_type, auth_vars),
        mcp_config_json=render_mcp_client_config(design),
        file_paths=sorted(f.path for f in files),
    )


def _render(template_name: str, context: dict[str, Any]) -> str:
    return _env.get_template(template_name).render(**context)


def generate_server(
    api: APIRepresentation,
    design: MCPServerDesign,
    preferences: Optional[GenerationPreferences] = None,
) -> GeneratedMCPServer:
    # No explicit preferences means "generate everything the design produced" --
    # GenerationPreferences() alone defaults include_destructive=False, which would
    # silently drop tools nobody asked to exclude.
    prefs = preferences if preferences is not None else GenerationPreferences(
        include_read_only=True, include_destructive=True
    )

    tools = _select_tools(design.tools, prefs)
    filtered_design = design.model_copy(update={"tools": tools})

    server_name = prefs.server_name or design.server_name or "mcp_server"
    description = prefs.description or design.description or f"MCP server for {api.name}."
    server_slug = _slug(server_name)
    auth_vars = _auth_vars_for(design.auth_type)

    groups = _group_tools(tools, prefs.group_by_resource)
    group_names = sorted(groups.keys())

    base_ctx = {
        "server_name": server_name,
        "server_slug": server_slug,
        "description": description,
        "api_name": api.name,
        "base_url": design.base_url,
        "auth_type": design.auth_type.value,
        "auth_header_name": design.auth_header_name or "X-API-Key",
        "needs_api_key": "API_KEY" in auth_vars,
        "needs_api_token": "API_TOKEN" in auth_vars,
        "auth_vars": auth_vars,
        "group_names": group_names,
        "generate_tests": prefs.generate_tests,
    }

    files: list[GeneratedFile] = []
    files.append(GeneratedFile(path="src/server.py", content=_render("server.py.j2", base_ctx)))
    files.append(GeneratedFile(path="src/config.py", content=_render("config.py.j2", base_ctx)))
    files.append(GeneratedFile(path="src/client.py", content=_render("client.py.j2", base_ctx)))

    model_blocks = [_model_block(tool) for tool in tools]
    files.append(
        GeneratedFile(
            path="src/models.py",
            content=_render("models.py.j2", {**base_ctx, "model_blocks": model_blocks}),
        )
    )
    files.append(GeneratedFile(path="src/tools/__init__.py", content=_render("tools_init.py.j2", base_ctx)))

    for group_name in group_names:
        group_tools = groups[group_name]
        tool_blocks = [_tool_source_block(tool) for tool in group_tools]
        model_imports = ", ".join(sorted({_model_name(tool) for tool in group_tools}))
        files.append(
            GeneratedFile(
                path=f"src/tools/{group_name}.py",
                content=_render(
                    "tool_module.py.j2",
                    {**base_ctx, "group_name": group_name, "tool_blocks": tool_blocks, "model_imports": model_imports},
                ),
            )
        )

    if prefs.generate_tests:
        files.append(GeneratedFile(path="tests/test_client.py", content=_render("test_client.py.j2", base_ctx)))
        files.append(GeneratedFile(path="tests/test_tools.py", content=_render("test_tools.py.j2", base_ctx)))

    files.append(
        GeneratedFile(path=".env.example", content=_render("env_example.j2", base_ctx), language="text")
    )
    files.append(GeneratedFile(path=".gitignore", content=_render("gitignore.j2", base_ctx), language="text"))
    files.append(
        GeneratedFile(
            path="requirements.txt", content=_render("requirements.txt.j2", base_ctx), language="text"
        )
    )
    files.append(
        GeneratedFile(path="pyproject.toml", content=_render("pyproject.toml.j2", base_ctx), language="toml")
    )
    files.append(
        GeneratedFile(path="mcp-config.json", content=render_mcp_client_config(filtered_design), language="json")
    )

    if prefs.generate_docs:
        files.append(
            GeneratedFile(path="README.md", content=render_readme(api, filtered_design, files), language="markdown")
        )

    return GeneratedMCPServer(files=files, server_name=server_name, tool_count=len(tools))
