"""Auto-generate professional README files."""
import logging
from typing import List
from app.models.mcp import MCPServerDesign, MCPTool

logger = logging.getLogger(__name__)


class AutoReadmeGenerator:
    """Generates professional README files for MCP servers."""

    def generate(self, design: MCPServerDesign) -> str:
        """Generate complete README.md file."""
        sections = [
            self._generate_header(design),
            self._generate_overview(design),
            self._generate_requirements(),
            self._generate_installation(),
            self._generate_environment_setup(),
            self._generate_configuration(design),
            self._generate_running(design),
            self._generate_tools_section(design),
            self._generate_authentication(design),
            self._generate_mcp_config(design),
            self._generate_examples(design),
            self._generate_troubleshooting(),
            self._generate_footer(),
        ]

        return "\n".join(sections)

    def _generate_header(self, design: MCPServerDesign) -> str:
        """Generate header section."""
        return f"""# {design.server_name.replace('_', ' ').title()}

{design.server_description}

**Version:** {design.version}

**API Source:** {design.api_base_url}
"""

    def _generate_overview(self, design: MCPServerDesign) -> str:
        """Generate overview section."""
        tool_count = len(design.tools)
        return f"""## Overview

This is an MCP (Model Context Protocol) server that provides a clean interface to the {design.source_api_name} API.

It exposes **{tool_count} tools** that allow Claude or other MCP clients to interact with the API through a structured interface.

### What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI assistants to interact with external tools and data sources. This server makes the {design.source_api_name} API available as MCP tools.
"""

    def _generate_requirements(self) -> str:
        """Generate requirements section."""
        return """## Requirements

- Python 3.8 or higher
- pip (Python package manager)
"""

    def _generate_installation(self) -> str:
        """Generate installation section."""
        return """## Installation

1. **Clone or download this project**

2. **Create a virtual environment** (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```
"""

    def _generate_environment_setup(self) -> str:
        """Generate environment setup section."""
        return """## Environment Setup

1. **Copy the example environment file**:

```bash
cp .env.example .env
```

2. **Edit `.env` and add your configuration**:

```env
API_BASE_URL=https://api.example.com
API_KEY=your-api-key-here
API_TOKEN=your-api-token-here
REQUEST_TIMEOUT=30
LOG_LEVEL=INFO
```

**Important:** Never commit your `.env` file. It contains sensitive credentials.
"""

    def _generate_configuration(self, design: MCPServerDesign) -> str:
        """Generate configuration section."""
        auth_note = ""
        if design.authentication_config:
            auth_type = design.authentication_config.get("type", "unknown")
            auth_note = f"""
### Authentication

This API requires **{auth_type}** authentication.

Configure your credentials in the `.env` file before running the server.
"""

        return f"""## Configuration

### Environment Variables

The following environment variables can be configured:

- `API_BASE_URL` - Base URL of the API (default: from spec)
- `API_KEY` - API key for authentication
- `API_TOKEN` - API token for authentication
- `REQUEST_TIMEOUT` - Request timeout in seconds (default: 30)
- `MAX_RETRIES` - Number of retries for failed requests (default: 3)
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO){auth_note}
"""

    def _generate_running(self, design: MCPServerDesign) -> str:
        """Generate running the server section."""
        return f"""## Running the Server

Start the MCP server:

```bash
python src/server.py
```

The server will start and be ready to receive requests from MCP clients.

### With logging enabled

For debugging, you can set the log level:

```bash
LOG_LEVEL=DEBUG python src/server.py
```
"""

    def _generate_tools_section(self, design: MCPServerDesign) -> str:
        """Generate tools documentation section."""
        if not design.tools:
            return "## Tools\n\nNo tools available.\n"

        tools_doc = "## Available Tools\n\n"
        tools_doc += f"This server exposes {len(design.tools)} tools:\n\n"

        for tool in design.tools:
            tools_doc += self._generate_tool_doc(tool)

        return tools_doc

    def _generate_tool_doc(self, tool: MCPTool) -> str:
        """Generate documentation for a single tool."""
        doc = f"""### `{tool.name}`

**Description:** {tool.description}

**HTTP Mapping:** `{tool.method} {tool.path}`

**Category:** {tool.category}

"""
        if tool.input_schema.properties:
            doc += "**Parameters:**\n\n"
            for param_name, param_schema in tool.input_schema.properties.items():
                required = "✓ required" if param_name in tool.input_schema.required else "optional"
                param_type = param_schema.get("type", "string")
                param_desc = param_schema.get("description", "")
                doc += f"- **{param_name}** ({param_type}) - {param_desc} [{required}]\n"
        else:
            doc += "**Parameters:** None\n"

        doc += "\n"

        if tool.example_request:
            doc += f"**Example Request:**\n\n```json\n{self._format_json(tool.example_request)}\n```\n\n"

        if tool.example_response:
            doc += f"**Example Response:**\n\n```json\n{self._format_json(tool.example_response)}\n```\n\n"

        return doc

    def _generate_authentication(self, design: MCPServerDesign) -> str:
        """Generate authentication section."""
        if not design.authentication_config:
            return """## Authentication

No authentication is required for this API.
"""

        auth_type = design.authentication_config.get("type", "unknown")
        auth_scheme = design.authentication_config.get("scheme", "Bearer")

        return f"""## Authentication

### {auth_type.title()} Authentication

This API uses **{auth_type}** authentication.

1. Obtain your credentials from the API provider
2. Add them to your `.env` file:
   - `API_KEY` for API key authentication
   - `API_TOKEN` for token-based authentication

3. The server will automatically include authentication headers in all requests

**Header:** `Authorization: {auth_scheme} <your-token>`
"""

    def _generate_mcp_config(self, design: MCPServerDesign) -> str:
        """Generate MCP client configuration section."""
        return f"""## MCP Client Configuration

To use this server with an MCP client (like Claude), configure it as follows:

### Claude Desktop

Edit your `claude_desktop_config.json` (located in `~/.config/Claude/` on Linux/Mac, or `%APPDATA%\\Claude\\` on Windows):

```json
{{
  "mcpServers": {{
    "{design.server_name}": {{
      "command": "python",
      "args": ["src/server.py"],
      "env": {{
        "API_BASE_URL": "{design.api_base_url}",
        "API_KEY": "your-key-here",
        "LOG_LEVEL": "INFO"
      }}
    }}
  }}
}}
```

### Generic MCP Client

```bash
python src/server.py
```

The server will run on stdio, ready to communicate with any MCP client.
"""

    def _generate_examples(self, design: MCPServerDesign) -> str:
        """Generate examples section."""
        examples = """## Examples

### Using with Claude

Once configured, you can ask Claude to use these tools:

- "Use the list_users tool to show me all users"
- "Call the get_user tool with ID 123"
- "Execute the create_user tool with name 'John Doe'"

Claude will automatically call the appropriate MCP tools.

### Direct Usage

You can also call tools programmatically:

```python
import asyncio
import json

async def call_tool():
    # This is a simplified example
    # See src/server.py for the actual implementation
    pass

asyncio.run(call_tool())
```
"""
        return examples

    def _generate_troubleshooting(self) -> str:
        """Generate troubleshooting section."""
        return """## Troubleshooting

### Module not found errors

**Problem:** `ModuleNotFoundError: No module named 'mcp'`

**Solution:**
```bash
pip install -r requirements.txt
```

### Connection refused

**Problem:** Cannot connect to the API

**Solution:**
1. Verify the API is accessible: `curl {API_BASE_URL}`
2. Check your internet connection
3. Verify `API_BASE_URL` is correct in your `.env` file

### Authentication errors

**Problem:** 401 Unauthorized or 403 Forbidden

**Solution:**
1. Verify your `API_KEY` or `API_TOKEN` is correct
2. Check that the authentication type matches the API requirements
3. Ensure credentials are in the `.env` file (not hardcoded)

### Request timeouts

**Problem:** Requests take too long or timeout

**Solution:**
1. Increase `REQUEST_TIMEOUT` in `.env`
2. Check your network connection
3. Verify the API is responding normally

### Debugging

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python src/server.py
```

This will show detailed information about each request and response.
"""

    def _generate_footer(self) -> str:
        """Generate footer section."""
        return """## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review the MCP specification: https://spec.modelcontextprotocol.io/
3. Check the API documentation at: {API_DOCS}

## License

This MCP server was auto-generated and is provided as-is.

The underlying API ({API_NAME}) has its own license and terms of service.
"""

    @staticmethod
    def _format_json(obj, indent: int = 2) -> str:
        """Format object as JSON string."""
        import json
        try:
            return json.dumps(obj, indent=indent)
        except:
            return str(obj)
