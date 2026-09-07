"""API discovery and representation models."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SecurityScheme(BaseModel):
    """OpenAPI security scheme."""
    type: str
    description: Optional[str] = None
    scheme: Optional[str] = None  # for HTTP
    bearerFormat: Optional[str] = None
    flows: Optional[Dict[str, Any]] = None  # for OAuth2


class Parameter(BaseModel):
    """API parameter definition."""
    name: str
    in_: str = Field(alias="in")
    description: Optional[str] = None
    required: bool = False
    schema: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class RequestBody(BaseModel):
    """API request body definition."""
    description: Optional[str] = None
    required: bool = False
    content: Dict[str, Any]


class Response(BaseModel):
    """API response definition."""
    status_code: str
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    schema: Optional[Dict[str, Any]] = None


class Endpoint(BaseModel):
    """Single API endpoint."""
    path: str
    method: str  # GET, POST, PUT, DELETE, PATCH, etc.
    summary: Optional[str] = None
    description: Optional[str] = None
    operation_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    parameters: List[Parameter] = Field(default_factory=list)
    request_body: Optional[RequestBody] = None
    responses: List[Response] = Field(default_factory=list)
    security: Optional[List[Dict[str, List[str]]]] = None


class APIRepresentation(BaseModel):
    """Normalized API representation."""
    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    base_url: Optional[str] = None
    source_url: str  # URL where API was discovered
    endpoints: List[Endpoint] = Field(default_factory=list)
    security_schemes: Dict[str, SecurityScheme] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)  # tag: description
    servers: List[Dict[str, Any]] = Field(default_factory=list)
    authentication_required: bool = False
    authentication_type: Optional[str] = None  # "api_key", "oauth2", "bearer", etc.


class DiscoveryResult(BaseModel):
    """Result of API discovery."""
    success: bool
    api: Optional[APIRepresentation] = None
    raw_spec: Optional[Dict[str, Any]] = None  # Raw OpenAPI/Swagger spec
    detected_type: Optional[str] = None  # "openapi3", "swagger2", "html_docs", etc.
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
