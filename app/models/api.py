"""Normalized internal representation of a discovered API."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ParamLocation(str, Enum):
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    COOKIE = "cookie"
    BODY = "body"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class SpecType(str, Enum):
    OPENAPI = "openapi"
    SWAGGER = "swagger"
    HTML_DOCS = "html_docs"
    NONE = "none"


class AuthType(str, Enum):
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    NONE = "none"
    UNKNOWN = "unknown"


class Parameter(BaseModel):
    name: str
    location: ParamLocation
    type: str = "string"
    required: bool = False
    description: str = ""
    default: Optional[Any] = None
    enum: list[str] = Field(default_factory=list)


class RequestBody(BaseModel):
    content_type: str = "application/json"
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")
    required: bool = False
    description: str = ""

    class Config:
        populate_by_name = True


class Response(BaseModel):
    status_code: str
    description: str = ""
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")

    class Config:
        populate_by_name = True


class SecurityScheme(BaseModel):
    type: AuthType
    scheme_name: str = ""
    header_name: Optional[str] = None
    bearer_format: Optional[str] = None
    description: str = ""


class Endpoint(BaseModel):
    path: str
    method: HttpMethod
    operation_id: str
    summary: str = ""
    description: str = ""
    parameters: list[Parameter] = Field(default_factory=list)
    request_body: Optional[RequestBody] = None
    responses: list[Response] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    security: list[str] = Field(default_factory=list)
    deprecated: bool = False
    destructive: bool = False
    source_ref: str = ""  # e.g. "openapi:/users:get" — provenance for anti-hallucination checks


class APIRepresentation(BaseModel):
    name: str
    description: str = ""
    base_url: str
    version: str = "unknown"
    servers: list[str] = Field(default_factory=list)
    authentication: list[SecurityScheme] = Field(default_factory=list)
    endpoints: list[Endpoint] = Field(default_factory=list)
    schemas: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiscoveryResult(BaseModel):
    source_url: str
    spec_type: SpecType
    spec_format: str = "json"  # json | yaml | html
    raw_spec: Optional[dict[str, Any]] = None
    discovered_pages: list[str] = Field(default_factory=list)
    success: bool
    error_message: Optional[str] = None
