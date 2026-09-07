"""MCP server code generator."""
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.models.mcp import MCPServerDesign, MCPTool

logger = logging.getLogger(__name__)


class MCPServerGenerator:
    """Generates complete MCP server projects."""

    def __init__(self):
        """Initialize the generator."""
        self.indent = "    "

    def generate_project(self, design: MCPServerDesign) -> Dict[str, str]:
        """Generate complete MCP server project files."""
        logger.info(f"Generating MCP server: {design.server_name}")

        files = {
            "src/server.py": self._generate_server(),
            "src/config.py": self._generate_config(design),
            "src/client.py": self._generate_client(design),
            "src/models.py": self._generate_models(design),
            "src/tools/__init__.py": self._generate_tools_init(design),
            "src/tools/api_tools.py": self._generate_api_tools(design),
            ".env.example": self._generate_env_example(design),
            ".gitignore": self._generate_gitignore(),
            "requirements.txt": self._generate_requirements(),
            "README.md": self._generate_readme(design),
            "mcp-config.json": self._generate_mcp_config(design),
            "pyproject.toml": self._generate_pyproject(design),
        }

        return files

    def _generate_server(self) -> str:
        """Generate main server.py file."""
        return '''"""MCP server initialization and tool registration."""
import logging
from typing import Any

from mcp.server import Server
from mcp.types import (
    Tool, TextContent, ToolResponse,
    ToolUseBlock
)

from config import Config
from tools.api_tools import create_tools

logger = logging.getLogger(__name__)


class MCPServerApp:
    """MCP Server application."""

    def __init__(self):
        """Initialize the MCP server."""
        self.config = Config()
        self.server = Server(self.config.server_name)
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools."""
        tools = create_tools(self.config)
        for tool in tools:
            self.server.tool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"]
            )(self._create_tool_handler(tool))

    def _create_tool_handler(self, tool: Dict[str, Any]):
        """Create a tool handler function."""
        async def handler(tool_input: Dict[str, Any]) -> ToolResponse:
            """Handle tool execution."""
            try:
                result = await self._execute_tool(tool, tool_input)
                return ToolResponse(
                    content=[TextContent(type="text", text=result)],
                    isError=False
                )
            except Exception as e:
                logger.error(f"Tool execution error in {tool['name']}: {e}")
                return ToolResponse(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )

        return handler

    async def _execute_tool(self, tool: Dict[str, Any], input_data: Dict[str, Any]) -> str:
        """Execute a tool and return results."""
        # This will be populated with actual tool execution logic
        raise NotImplementedError(f"Tool {tool['name']} not implemented")

    def run(self):
        """Run the MCP server."""
        logger.info(f"Starting {self.config.server_name}...")
        self.server.run()


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    app = MCPServerApp()
    app.run()
'''

    def _generate_config(self, design: MCPServerDesign) -> str:
        """Generate config.py file."""
        auth_type = design.authentication_config.get("type", "none") if design.authentication_config else "none"

        return f'''"""Configuration management for MCP server."""
import os
from typing import Optional


class Config:
    """Server configuration."""

    # Server metadata
    server_name = "{design.server_name}"
    server_description = "{design.server_description}"
    server_version = "{design.version}"

    # API Configuration
    api_base_url = "{design.api_base_url}"
    api_key = os.getenv("API_KEY", "")
    api_token = os.getenv("API_TOKEN", "")

    # Authentication
    auth_type = "{auth_type}"
    auth_header_name = os.getenv("AUTH_HEADER_NAME", "Authorization")
    auth_scheme = os.getenv("AUTH_SCHEME", "Bearer")

    # Limits
    request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
    max_retries = int(os.getenv("MAX_RETRIES", "3"))

    # Logging
    log_level = os.getenv("LOG_LEVEL", "INFO")

    def get_auth_header(self) -> Optional[dict]:
        """Get authentication header for API requests."""
        if not self.api_key and not self.api_token:
            return None

        token = self.api_key or self.api_token
        if self.auth_type == "bearer":
            return {{"Authorization": f"Bearer {{token}}"}}
        elif self.auth_type == "api_key":
            return {{"X-API-Key": token}}
        elif self.auth_type == "basic":
            return {{"Authorization": f"Basic {{token}}"}}

        return None

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {{
            "server_name": self.server_name,
            "server_description": self.server_description,
            "server_version": self.server_version,
            "api_base_url": self.api_base_url,
            "auth_type": self.auth_type,
        }}
'''

    def _generate_client(self, design: MCPServerDesign) -> str:
        """Generate client.py file."""
        return f'''"""API client for calling the discovered API."""
import logging
from typing import Any, Dict, Optional
import json
import httpx

from config import Config

logger = logging.getLogger(__name__)


class APIClient:
    """Client for making API requests."""

    def __init__(self, config: Config):
        """Initialize the API client."""
        self.config = config
        self.base_url = config.api_base_url.rstrip("/")
        self.timeout = config.request_timeout

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make an API request."""
        url = f"{{self.base_url}}{{path}}"

        # Prepare headers
        req_headers = headers or {{}}
        auth_header = self.config.get_auth_header()
        if auth_header:
            req_headers.update(auth_header)

        # Make request
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    headers=req_headers,
                )
                response.raise_for_status()

                # Try to parse JSON response
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {{"text": response.text}}

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {{e.response.status_code}}: {{e}}")
                raise
            except Exception as e:
                logger.error(f"Request error: {{e}}")
                raise

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a GET request."""
        return await self.request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a POST request."""
        return await self.request(
            "POST", path, params=params, json_body=json_body, headers=headers
        )

    async def put(
        self,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self.request(
            "PUT", path, params=params, json_body=json_body, headers=headers
        )

    async def delete(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self.request("DELETE", path, params=params, headers=headers)
'''

    def _generate_models(self, design: MCPServerDesign) -> str:
        """Generate models.py file."""
        return '''"""Pydantic models for API responses."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class APIResponse(BaseModel):
    """Generic API response model."""
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    class Config:
        extra = "allow"
'''

    def _generate_tools_init(self, design: MCPServerDesign) -> str:
        """Generate tools/__init__.py file."""
        return '''"""MCP tools module."""
'''

    def _generate_api_tools(self, design: MCPServerDesign) -> str:
        """Generate tools/api_tools.py file."""
        tools_code = "\"\"\"API tools for MCP server.\"\"\"\nfrom typing import List, Dict, Any\n\n"

        tools_code += "def create_tools(config) -> List[Dict[str, Any]]:\n"
        tools_code += f'{self.indent}"""Create all available MCP tools."""\n'
        tools_code += f'{self.indent}tools = [\n'

        for tool in design.tools:
            tools_code += self._generate_tool_definition(tool)

        tools_code += f'{self.indent}]\n'
        tools_code += f'{self.indent}return tools\n'

        return tools_code

    def _generate_tool_definition(self, tool: MCPTool) -> str:
        """Generate a single tool definition."""
        schema = {
            "type": "object",
            "properties": tool.input_schema.properties,
            "required": tool.input_schema.required
        }

        # Escape quotes outside f-string to avoid backslash in expression
        escaped_desc = tool.description.replace('"', r'\"')
        schema_str = str(schema).replace("'", '"')

        code = f'''{self.indent * 2}{{
{self.indent * 3}"name": "{tool.name}",
{self.indent * 3}"description": "{escaped_desc}",
{self.indent * 3}"inputSchema": {schema_str},
{self.indent * 3}"method": "{tool.method}",
{self.indent * 3}"path": "{tool.path}",
{self.indent * 3}"category": "{tool.category}",
{self.indent * 2}}},
'''

        return code

    def _generate_env_example(self, design: MCPServerDesign) -> str:
        """Generate .env.example file."""
        env = f"""# API Configuration
API_BASE_URL={design.api_base_url}
API_KEY=your-api-key-here
API_TOKEN=your-api-token-here

# Authentication
AUTH_HEADER_NAME=Authorization
AUTH_SCHEME=Bearer

# Server Configuration
REQUEST_TIMEOUT=30
MAX_RETRIES=3
LOG_LEVEL=INFO
"""
        return env

    def _generate_gitignore(self) -> str:
        """Generate .gitignore file."""
        return """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Environment
.env
.env.local
.env.*.local

# Testing
.pytest_cache/
.coverage
htmlcov/

# Project specific
*.log
"""

    def _generate_requirements(self) -> str:
        """Generate requirements.txt file."""
        return """mcp>=0.1.0
httpx>=0.24.0
pydantic>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
"""

    def _generate_readme(self, design: MCPServerDesign) -> str:
        """Generate README.md file."""
        from app.services.auto_readme import AutoReadmeGenerator

        generator = AutoReadmeGenerator()
        return generator.generate(design)

    def _generate_mcp_config(self, design: MCPServerDesign) -> str:
        """Generate mcp-config.json example."""
        config = f'''{{
  "mcpServers": {{
    "{design.server_name}": {{
      "command": "python",
      "args": ["src/server.py"],
      "env": {{
        "API_BASE_URL": "{design.api_base_url}",
        "API_KEY": "",
        "LOG_LEVEL": "INFO"
      }}
    }}
  }}
}}
'''
        return config

    def _generate_pyproject(self, design: MCPServerDesign) -> str:
        """Generate pyproject.toml file."""
        return f'''[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{design.server_name}"
version = "{design.version}"
description = "{design.server_description}"
requires-python = ">=3.8"
dependencies = [
    "mcp>=0.1.0",
    "httpx>=0.24.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
]

[project.scripts]
{design.server_name} = "src.server:main"
'''
