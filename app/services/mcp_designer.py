"""AI-powered MCP tool designer using OpenAI."""
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ValidationError

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.models.api import APIRepresentation
from app.models.mcp import MCPTool, MCPServerDesign, ToolInputSchema, ToolParameter

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class ToolDesignResponse(BaseModel):
    """Response from OpenAI containing MCP tool design."""
    server_name: str
    server_description: str
    tools: List[Dict[str, Any]]
    reasoning: Optional[str] = None


class MCPDesigner:
    """AI-powered MCP tool designer."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the designer with OpenAI API key."""
        if not OpenAI:
            raise ImportError("OpenAI package required: pip install openai")
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=self.api_key)
        self.model = OPENAI_MODEL

    def design_tools(self, api: APIRepresentation) -> MCPServerDesign:
        """Design MCP tools from discovered API."""
        logger.info(f"Designing MCP tools for {api.name}")

        # Prepare the API summary for the model
        api_summary = self._summarize_api(api)

        # Create prompt for GPT-4 mini
        prompt = self._create_design_prompt(api, api_summary)

        # Call OpenAI
        response_text = self._call_openai(prompt)

        # Parse response
        tool_design = self._parse_design_response(response_text, api)

        logger.info(f"Designed {len(tool_design.tools)} MCP tools")
        return tool_design

    def _summarize_api(self, api: APIRepresentation) -> str:
        """Create a concise summary of the API for the model."""
        summary = f"""
API Name: {api.name}
Description: {api.description or 'No description'}
Version: {api.version or 'Unknown'}
Base URL: {api.base_url or api.source_url}
Total Endpoints: {len(api.endpoints)}
Authentication Type: {api.authentication_type or 'None'}

Endpoints:
"""
        for endpoint in api.endpoints[:50]:  # Limit to first 50 for token efficiency
            summary += f"\n- {endpoint.method} {endpoint.path}"
            if endpoint.summary:
                summary += f" - {endpoint.summary}"
            if endpoint.parameters:
                params = ", ".join([p.name for p in endpoint.parameters[:5]])
                summary += f" (params: {params})"

        return summary

    def _create_design_prompt(self, api: APIRepresentation, api_summary: str) -> str:
        """Create the prompt for MCP tool design."""
        return f"""You are an expert API designer. Analyze this API and design useful MCP tools.

{api_summary}

Please design MCP tools that:
1. Group related endpoints logically
2. Provide clean, developer-friendly interfaces
3. Include only endpoints that are genuinely useful (not duplicate operations)
4. Use clear, descriptive tool names in snake_case
5. Define proper input schemas with required/optional parameters
6. Handle authentication transparently

Respond with ONLY valid JSON (no markdown, no code blocks, no explanations):
{{
  "server_name": "descriptive_name_for_mcp_server",
  "server_description": "Clear description of what this MCP server does",
  "tools": [
    {{
      "name": "tool_name",
      "description": "What this tool does",
      "category": "read|write|admin",
      "method": "GET|POST|PUT|DELETE|PATCH",
      "path": "/api/endpoint/path",
      "parameters": [
        {{
          "name": "param_name",
          "type": "string|number|integer|boolean",
          "description": "Parameter description",
          "required": true,
          "enum": null
        }}
      ],
      "example_request": {{}},
      "example_response": {{}}
    }}
  ]
}}"""

    def _call_openai(self, prompt: str, max_retries: int = 3) -> str:
        """Call OpenAI API with retry logic."""
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                return response.content[0].text
            except Exception as e:
                logger.warning(f"OpenAI API attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                continue

    def _parse_design_response(
        self, response_text: str, api: APIRepresentation
    ) -> MCPServerDesign:
        """Parse OpenAI response into MCPServerDesign."""
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        try:
            data = json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            # Fallback: create a simple design
            return self._create_fallback_design(api)

        try:
            # Convert tool data to MCPTool objects
            tools = []
            for tool_data in data.get("tools", []):
                tool = self._convert_tool_data(tool_data, api)
                if tool:
                    tools.append(tool)

            return MCPServerDesign(
                server_name=data.get("server_name", f"{api.name}_mcp"),
                server_description=data.get(
                    "server_description",
                    f"MCP server for {api.name}"
                ),
                version="0.1.0",
                tools=tools,
                api_base_url=api.base_url or api.source_url,
                source_api_name=api.name,
                authentication_config=self._extract_auth_config(api)
            )
        except Exception as e:
            logger.error(f"Error converting tool data: {e}")
            return self._create_fallback_design(api)

    def _convert_tool_data(
        self, tool_data: Dict[str, Any], api: APIRepresentation
    ) -> Optional[MCPTool]:
        """Convert tool data from AI response to MCPTool."""
        try:
            # Validate that the endpoint exists in the API
            endpoint_path = tool_data.get("path", "")
            method = tool_data.get("method", "GET")

            # Find matching endpoint
            matching_endpoint = None
            for endpoint in api.endpoints:
                if endpoint.path == endpoint_path and endpoint.method == method:
                    matching_endpoint = endpoint
                    break

            # Build input schema
            properties = {}
            required = []
            for param in tool_data.get("parameters", []):
                param_name = param.get("name", "")
                if param_name:
                    properties[param_name] = {
                        "type": param.get("type", "string"),
                        "description": param.get("description", "")
                    }
                    if param.get("enum"):
                        properties[param_name]["enum"] = param.get("enum")
                    if param.get("required", False):
                        required.append(param_name)

            input_schema = ToolInputSchema(
                type="object",
                properties=properties,
                required=required
            )

            # Convert parameters
            parameters = []
            for param in tool_data.get("parameters", []):
                parameters.append(ToolParameter(
                    name=param.get("name", ""),
                    type=param.get("type", "string"),
                    description=param.get("description", ""),
                    required=param.get("required", False),
                    enum=param.get("enum")
                ))

            return MCPTool(
                name=tool_data.get("name", ""),
                description=tool_data.get("description", ""),
                category=tool_data.get("category", "read"),
                api_endpoint=f"{method} {endpoint_path}",
                method=method,
                path=endpoint_path,
                parameters=parameters,
                input_schema=input_schema,
                required_auth=self._get_auth_requirement(api),
                example_request=tool_data.get("example_request"),
                example_response=tool_data.get("example_response")
            )
        except Exception as e:
            logger.warning(f"Failed to convert tool {tool_data.get('name')}: {e}")
            return None

    def _extract_auth_config(self, api: APIRepresentation) -> Optional[Dict[str, Any]]:
        """Extract authentication configuration from API."""
        if not api.authentication_required:
            return None

        auth_config = {
            "type": api.authentication_type or "unknown",
            "required": True
        }

        if api.security_schemes:
            auth_config["schemes"] = {}
            for name, scheme in api.security_schemes.items():
                auth_config["schemes"][name] = {
                    "type": scheme.type,
                    "description": scheme.description
                }

        return auth_config

    def _get_auth_requirement(self, api: APIRepresentation) -> Optional[str]:
        """Get auth requirement string for a tool."""
        if api.authentication_required:
            return f"{api.authentication_type or 'api_key'}_required"
        return None

    def _create_fallback_design(self, api: APIRepresentation) -> MCPServerDesign:
        """Create a fallback design if AI parsing fails."""
        logger.warning("Using fallback design for API")

        tools = []
        for endpoint in api.endpoints[:20]:  # Limit to first 20 endpoints
            # Create simple tool name from path
            tool_name = self._path_to_tool_name(endpoint.path, endpoint.method)

            # Build input schema from parameters
            properties = {}
            required = []
            for param in endpoint.parameters:
                param_name = param.name
                properties[param_name] = {
                    "type": param.schema.get("type", "string") if param.schema else "string",
                    "description": param.description or ""
                }
                if param.required:
                    required.append(param_name)

            input_schema = ToolInputSchema(
                type="object",
                properties=properties,
                required=required
            )

            tools.append(MCPTool(
                name=tool_name,
                description=endpoint.summary or endpoint.description or f"{endpoint.method} {endpoint.path}",
                category="read" if endpoint.method == "GET" else "write",
                api_endpoint=f"{endpoint.method} {endpoint.path}",
                method=endpoint.method,
                path=endpoint.path,
                parameters=[],
                input_schema=input_schema,
                required_auth=self._get_auth_requirement(api)
            ))

        return MCPServerDesign(
            server_name=f"{api.name.lower().replace(' ', '_')}_mcp",
            server_description=api.description or f"MCP server for {api.name}",
            version="0.1.0",
            tools=tools,
            api_base_url=api.base_url or api.source_url,
            source_api_name=api.name,
            authentication_config=self._extract_auth_config(api)
        )

    @staticmethod
    def _path_to_tool_name(path: str, method: str) -> str:
        """Convert API path to MCP tool name."""
        # Remove leading/trailing slashes
        path = path.strip("/")
        # Replace path parameters with "id" or similar
        path = path.replace("{", "").replace("}", "")
        # Replace slashes with underscores
        path = path.replace("/", "_")
        # Remove hyphens
        path = path.replace("-", "_")
        # Add method prefix for non-GET requests
        if method != "GET":
            path = f"{method.lower()}_{path}"
        return path
