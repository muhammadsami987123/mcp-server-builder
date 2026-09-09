"""MCP tool design and generated-server artifact models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.api import AuthType, HttpMethod


class MCPParameter(BaseModel):
    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Optional[Any] = None


class MCPTool(BaseModel):
    name: str
    description: str
    method: HttpMethod
    path: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    parameters: list[MCPParameter] = Field(default_factory=list)
    source_operation_id: str
    group: str = "general"
    destructive: bool = False
    selected: bool = True


class MCPServerDesign(BaseModel):
    server_name: str
    description: str
    tools: list[MCPTool] = Field(default_factory=list)
    base_url: str
    auth_type: AuthType = AuthType.NONE
    auth_header_name: Optional[str] = None
    ignored_endpoints: list[str] = Field(default_factory=list)
    reasoning: str = ""


class GeneratedFile(BaseModel):
    path: str
    content: str
    language: str = "python"


class GeneratedMCPServer(BaseModel):
    files: list[GeneratedFile] = Field(default_factory=list)
    server_name: str
    tool_count: int = 0


class ValidationCheck(BaseModel):
    name: str
    passed: bool
    message: str = ""
    severity: str = "error"  # error | warning


class ValidationResult(BaseModel):
    passed: bool
    checks: list[ValidationCheck] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GenerationPreferences(BaseModel):
    server_name: Optional[str] = None
    description: Optional[str] = None
    tool_naming_style: str = "snake_case"
    include_read_only: bool = True
    include_destructive: bool = False
    group_by_resource: bool = True
    generate_tests: bool = True
    generate_docs: bool = True
    selected_tool_names: Optional[list[str]] = None


class MCPProject(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    source_url: str
    status: str = "pending"  # pending|discovering|analyzing|designing|generating|validating|ready|failed
    api: Optional[dict[str, Any]] = None  # APIRepresentation.model_dump()
    design: Optional[dict[str, Any]] = None  # MCPServerDesign.model_dump()
    generated: Optional[dict[str, Any]] = None  # GeneratedMCPServer.model_dump()
    validation: Optional[dict[str, Any]] = None  # ValidationResult.model_dump()
    preferences: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
