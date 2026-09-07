"""OpenAI integration for MCP tool design."""
import json
from typing import Optional

from openai import AsyncOpenAI, APIError

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.models.api import APIRepresentation
from app.models.mcp import MCPServerDesign, MCPTool, ToolInputSchema


class OpenAIService:
    """Design MCP tools using OpenAI."""

    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL

    async def design_tools(
        self,
        api: APIRepresentation,
        max_tools: int = 10,
    ) -> tuple[bool, Optional[MCPServerDesign], list]:
        """
        Design MCP tools from API representation.

        Args:
            api: Discovered and analyzed API
            max_tools: Maximum number of tools to design

        Returns:
            (success, MCPServerDesign, errors)
        """
        errors = []

        # Prepare API description for Claude
        api_summary = self._prepare_api_summary(api, max_tools)

        # Prepare prompt
        prompt = self._prepare_design_prompt(api_summary, api)

        try:
            # Call GPT-4-Turbo
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # Extract response
            response_text = message.content[0].text if message.content else ""

            # Parse JSON from response
            design = self._parse_design_response(response_text, api)

            return True, design, errors

        except APIError as e:
            errors.append(f"OpenAI API error: {str(e)}")
            return False, None, errors
        except Exception as e:
            errors.append(f"Tool design failed: {str(e)}")
            return False, None, errors

    def _prepare_api_summary(self, api: APIRepresentation, max_tools: int) -> str:
        """Prepare concise API summary for Claude."""
        endpoints = api.endpoints[:max_tools]

        summary = f"""
API Name: {api.name}
Description: {api.description or "No description"}
Version: {api.version or "Unknown"}
Base URL: {api.base_url or "Unknown"}

Endpoints ({len(endpoints)} of {len(api.endpoints)}):
"""
        for endpoint in endpoints:
            summary += f"\n- {endpoint.method} {endpoint.path}"
            if endpoint.summary:
                summary += f": {endpoint.summary}"
            elif endpoint.description:
                summary += f": {endpoint.description}"

            if endpoint.parameters:
                summary += "\n  Parameters:"
                for param in endpoint.parameters[:5]:  # Limit to 5 params
                    summary += f"\n    - {param.name} ({param.in_}): {param.description or 'No description'}"

        return summary

    def _prepare_design_prompt(self, api_summary: str, api: APIRepresentation) -> str:
        """Prepare Claude prompt for tool design."""
        return f"""You are an expert at designing Model Context Protocol (MCP) tools.

Given this API specification:

{api_summary}

Design MCP tools to expose the most useful endpoints. For each tool:
1. Create a descriptive name (snake_case)
2. Write a clear, concise description
3. Identify the category (data_retrieval, data_modification, analysis, etc.)
4. Map to the specific API endpoint
5. Define input schema with parameters from the endpoint
6. Include type information and descriptions

IMPORTANT: Return ONLY a valid JSON object with this structure (no markdown, no code blocks):
{{
  "tools": [
    {{
      "name": "tool_name",
      "description": "What this tool does",
      "category": "data_retrieval",
      "api_endpoint": "GET /path/{{id}}",
      "method": "GET",
      "path": "/path/{{id}}",
      "parameters": [
        {{
          "name": "id",
          "type": "string",
          "description": "User ID",
          "required": true
        }}
      ],
      "input_schema": {{
        "type": "object",
        "properties": {{
          "id": {{
            "type": "string",
            "description": "User ID"
          }}
        }},
        "required": ["id"],
        "description": "User lookup parameters"
      }}
    }}
  ]
}}

Focus on practical, widely-used endpoints. Limit to 10 tools maximum."""

    def _parse_design_response(
        self,
        response_text: str,
        api: APIRepresentation,
    ) -> Optional[MCPServerDesign]:
        """Parse Claude's response into MCPServerDesign."""
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end <= json_start:
                return None

            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            # Convert to MCPTool objects
            tools = []
            for tool_data in data.get("tools", []):
                try:
                    # Ensure input_schema is valid
                    input_schema = tool_data.get("input_schema", {})
                    if not isinstance(input_schema, dict):
                        input_schema = {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        }

                    tool = MCPTool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        category=tool_data.get("category"),
                        api_endpoint=tool_data.get("api_endpoint", ""),
                        method=tool_data.get("method", "GET"),
                        path=tool_data.get("path", ""),
                        parameters=tool_data.get("parameters", []),
                        input_schema=ToolInputSchema(**input_schema),
                    )
                    tools.append(tool)
                except Exception as e:
                    pass

            # Create server design
            server_name = f"{api.name.lower().replace(' ', '_')}_mcp"
            design = MCPServerDesign(
                server_name=server_name,
                server_description=f"MCP server for {api.name}",
                version="0.1.0",
                tools=tools,
                api_base_url=api.base_url or "",
                source_api_name=api.name,
            )

            return design

        except Exception as e:
            return None
