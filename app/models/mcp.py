"""MCP tool design and generation models."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """MCP tool parameter definition."""
    name: str
    type: str  # "string", "number", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None
    properties: Optional[Dict[str, Any]] = None  # for object type


class ToolInputSchema(BaseModel):
    """JSON Schema for tool input."""
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class MCPTool(BaseModel):
    """Single MCP tool definition."""
    name: str
    description: str
    category: Optional[str] = None  # e.g., "data_retrieval", "data_modification"
    api_endpoint: str  # e.g., "GET /users/{id}"
    method: str  # HTTP method
    path: str  # API path
    parameters: List[ToolParameter] = Field(default_factory=list)
    input_schema: ToolInputSchema
    required_auth: Optional[str] = None
    rate_limit_info: Optional[str] = None
    example_request: Optional[Dict[str, Any]] = None
    example_response: Optional[Dict[str, Any]] = None


class MCPServerDesign(BaseModel):
    """Complete MCP server design."""
    server_name: str
    server_description: str
    version: str = "0.1.0"
    tools: List[MCPTool] = Field(default_factory=list)
    authentication_config: Optional[Dict[str, Any]] = None
    api_base_url: str
    source_api_name: str


class GeneratedMCPServer(BaseModel):
    """Generated MCP server code."""
    server_name: str
    main_file: str  # main.py content
    tools_file: str  # tools.py content
    utils_file: Optional[str] = None  # utils.py content
    requirements_file: str  # requirements.txt content
    config_file: Optional[str] = None  # config.py or .env.example
    readme_file: str  # README.md
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ProjectFile(BaseModel):
    """Single project file."""
    path: str
    content: str
    file_type: str = "text"  # "text", "binary"


class MCPProject(BaseModel):
    """Complete MCP project state."""
    project_id: str
    name: str
    description: str
    source_url: str
    source_api_name: str
    created_at: str  # ISO format
    discovery_report: Dict[str, Any]  # raw discovery result
    design: MCPServerDesign  # tool design
    generated_files: List[ProjectFile]  # generated code files
    status: str = "completed"  # "discovering", "designing", "generating", "completed", "error"
    error_message: Optional[str] = None
