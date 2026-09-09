"""OpenAPI 3.x and Swagger 2.0 parsing into the internal APIRepresentation model."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.models.api import (
    APIRepresentation,
    AuthType,
    Endpoint,
    HttpMethod,
    ParamLocation,
    Parameter,
    RequestBody,
    Response,
    SecurityScheme,
)

_OPERATION_METHODS = ("get", "put", "post", "delete", "options", "head", "patch")


def detect_spec_version(raw_spec: dict) -> str:
    """Returns "openapi3" or "swagger2"."""
    if not isinstance(raw_spec, dict):
        raise ValueError("Spec must be a JSON object")

    openapi_ver = raw_spec.get("openapi")
    if isinstance(openapi_ver, str) and openapi_ver.startswith("3"):
        return "openapi3"

    swagger_ver = raw_spec.get("swagger")
    if isinstance(swagger_ver, str) and swagger_ver.startswith("2"):
        return "swagger2"

    if isinstance(raw_spec.get("paths"), dict):
        # Structurally looks like a spec but lacks an explicit version marker;
        # OpenAPI 3 shape is the more common modern default.
        return "openapi3"

    raise ValueError("Could not detect OpenAPI/Swagger version from spec")


def _slugify_path(path: str) -> str:
    slug = path.strip("/").replace("{", "").replace("}", "")
    slug = slug.replace("/", "_").replace("-", "_")
    return slug or "root"


def _extract_base_url(raw_spec: dict, source_url: str, version: str) -> tuple[str, list[str]]:
    parsed_source = urlparse(source_url)
    origin = f"{parsed_source.scheme}://{parsed_source.netloc}" if parsed_source.netloc else source_url

    if version == "openapi3":
        servers = raw_spec.get("servers") or []
        urls = []
        for s in servers:
            if isinstance(s, dict) and s.get("url"):
                url = s["url"]
                if url.startswith("/"):
                    url = origin.rstrip("/") + url
                urls.append(url)
        base_url = urls[0] if urls else origin
        return base_url, urls or [base_url]

    host = raw_spec.get("host")
    base_path = raw_spec.get("basePath", "") or ""
    schemes = raw_spec.get("schemes") or ["https"]
    if host:
        base_url = f"{schemes[0]}://{host}{base_path}"
        return base_url, [base_url]
    return origin, [origin]


def _auth_type_from_openapi3(scheme: dict) -> AuthType:
    scheme_type = (scheme.get("type") or "").lower()
    if scheme_type == "apikey":
        return AuthType.API_KEY
    if scheme_type == "http":
        http_scheme = (scheme.get("scheme") or "").lower()
        if http_scheme == "bearer":
            return AuthType.BEARER
        if http_scheme == "basic":
            return AuthType.BASIC
        return AuthType.UNKNOWN
    if scheme_type == "oauth2":
        return AuthType.OAUTH2
    if scheme_type == "openidconnect":
        return AuthType.OAUTH2
    return AuthType.UNKNOWN


def _auth_type_from_swagger2(scheme: dict) -> AuthType:
    scheme_type = (scheme.get("type") or "").lower()
    if scheme_type == "apikey":
        return AuthType.API_KEY
    if scheme_type == "basic":
        return AuthType.BASIC
    if scheme_type == "oauth2":
        return AuthType.OAUTH2
    return AuthType.UNKNOWN


def extract_security_schemes(raw_spec: dict) -> list[SecurityScheme]:
    """Parses components.securitySchemes (OpenAPI 3) or securityDefinitions
    (Swagger 2) into SecurityScheme models. Never includes actual secrets."""
    try:
        version = detect_spec_version(raw_spec)
    except ValueError:
        return []

    schemes: list[SecurityScheme] = []
    if version == "openapi3":
        raw_schemes = (raw_spec.get("components") or {}).get("securitySchemes") or {}
        for name, scheme in raw_schemes.items():
            if not isinstance(scheme, dict):
                continue
            schemes.append(
                SecurityScheme(
                    type=_auth_type_from_openapi3(scheme),
                    scheme_name=name,
                    header_name=scheme.get("name") if scheme.get("in") == "header" else None,
                    bearer_format=scheme.get("bearerFormat"),
                    description=scheme.get("description", ""),
                )
            )
    else:
        raw_schemes = raw_spec.get("securityDefinitions") or {}
        for name, scheme in raw_schemes.items():
            if not isinstance(scheme, dict):
                continue
            schemes.append(
                SecurityScheme(
                    type=_auth_type_from_swagger2(scheme),
                    scheme_name=name,
                    header_name=scheme.get("name") if scheme.get("in") == "header" else None,
                    bearer_format=None,
                    description=scheme.get("description", ""),
                )
            )
    return schemes


def _flatten_security_requirement(security: list[dict] | None) -> list[str]:
    names: list[str] = []
    for requirement in security or []:
        if isinstance(requirement, dict):
            names.extend(requirement.keys())
    return names


def _parse_parameter_openapi3(p: dict) -> Parameter | None:
    location_raw = p.get("in")
    if location_raw not in ("query", "path", "header", "cookie"):
        return None
    schema = p.get("schema") or {}
    enum = schema.get("enum") or []
    return Parameter(
        name=p.get("name", ""),
        location=ParamLocation(location_raw),
        type=schema.get("type", "string"),
        required=bool(p.get("required", False)) or location_raw == "path",
        description=p.get("description", ""),
        default=schema.get("default"),
        enum=[str(v) for v in enum],
    )


def _parse_parameter_swagger2(p: dict) -> Parameter | None:
    location_raw = p.get("in")
    if location_raw not in ("query", "path", "header", "formData"):
        return None
    # formData has no first-class ParamLocation; body-shaped, closest analog is BODY.
    location = ParamLocation.BODY if location_raw == "formData" else ParamLocation(location_raw)
    enum = p.get("enum") or []
    return Parameter(
        name=p.get("name", ""),
        location=location,
        type=p.get("type", "string"),
        required=bool(p.get("required", False)) or location_raw == "path",
        description=p.get("description", ""),
        default=p.get("default"),
        enum=[str(v) for v in enum],
    )


def _request_body_openapi3(op: dict) -> RequestBody | None:
    rb = op.get("requestBody")
    if not isinstance(rb, dict):
        return None
    content = rb.get("content") or {}
    content_type = next(iter(content.keys()), "application/json")
    body_schema: dict[str, Any] = {}
    if content_type in content and isinstance(content[content_type], dict):
        body_schema = content[content_type].get("schema") or {}
    return RequestBody(
        content_type=content_type,
        schema=body_schema,
        required=bool(rb.get("required", False)),
        description=rb.get("description", ""),
    )


def _request_body_swagger2(operation_params: list[dict], consumes: list[str]) -> RequestBody | None:
    body_param = next((p for p in operation_params if isinstance(p, dict) and p.get("in") == "body"), None)
    if not body_param:
        return None
    content_type = consumes[0] if consumes else "application/json"
    return RequestBody(
        content_type=content_type,
        schema=body_param.get("schema") or {},
        required=bool(body_param.get("required", False)),
        description=body_param.get("description", ""),
    )


def _extract_responses(responses: dict, version: str) -> list[Response]:
    result: list[Response] = []
    for status_code, resp in (responses or {}).items():
        if not isinstance(resp, dict):
            continue
        description = resp.get("description", "")
        resp_schema: dict[str, Any] = {}
        if version == "openapi3":
            content = resp.get("content") or {}
            first_media = next(iter(content.values()), None)
            if isinstance(first_media, dict):
                resp_schema = first_media.get("schema") or {}
        else:
            resp_schema = resp.get("schema") or {}
        result.append(Response(status_code=str(status_code), description=description, schema=resp_schema))
    return result


def parse_openapi(raw_spec: dict, source_url: str) -> APIRepresentation:
    """Parses a full OpenAPI 3.x or Swagger 2.0 document into an APIRepresentation."""
    version = detect_spec_version(raw_spec)
    info = raw_spec.get("info") or {}
    base_url, servers = _extract_base_url(raw_spec, source_url, version)
    security_schemes = extract_security_schemes(raw_spec)
    global_security = raw_spec.get("security")
    consumes = raw_spec.get("consumes") or []

    paths = raw_spec.get("paths") or {}
    endpoints: list[Endpoint] = []

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        path_level_params = [p for p in (path_item.get("parameters") or []) if isinstance(p, dict) and "$ref" not in p]

        for method in _OPERATION_METHODS:
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue

            http_method = HttpMethod(method.upper())
            op_params = [p for p in (op.get("parameters") or []) if isinstance(p, dict) and "$ref" not in p]
            combined_raw_params = path_level_params + op_params

            parser_fn = _parse_parameter_openapi3 if version == "openapi3" else _parse_parameter_swagger2
            parsed: dict[tuple[str, str], Parameter] = {}
            for raw_param in combined_raw_params:
                if raw_param.get("in") == "body":
                    continue
                param = parser_fn(raw_param)
                if param is not None:
                    parsed[(param.name, param.location.value)] = param
            parameters = list(parsed.values())

            if version == "openapi3":
                request_body = _request_body_openapi3(op)
            else:
                op_consumes = op.get("consumes") or consumes
                request_body = _request_body_swagger2(combined_raw_params, op_consumes)

            responses = _extract_responses(op.get("responses") or {}, version)

            operation_id = op.get("operationId") or f"{method}_{_slugify_path(path)}"
            op_security = op.get("security", global_security)

            has_path_param = "{" in path
            destructive = http_method == HttpMethod.DELETE or (
                http_method in (HttpMethod.PUT, HttpMethod.PATCH) and has_path_param
            )

            endpoints.append(
                Endpoint(
                    path=path,
                    method=http_method,
                    operation_id=operation_id,
                    summary=op.get("summary", ""),
                    description=op.get("description", ""),
                    parameters=parameters,
                    request_body=request_body,
                    responses=responses,
                    tags=list(op.get("tags") or []),
                    security=_flatten_security_requirement(op_security),
                    deprecated=bool(op.get("deprecated", False)),
                    destructive=destructive,
                    source_ref=f"openapi:{method}:{path}",
                )
            )

    schemas = {}
    if version == "openapi3":
        schemas = (raw_spec.get("components") or {}).get("schemas") or {}
    else:
        schemas = raw_spec.get("definitions") or {}

    return APIRepresentation(
        name=info.get("title", "Untitled API"),
        description=info.get("description", ""),
        base_url=base_url,
        version=str(info.get("version", "unknown")),
        servers=servers,
        authentication=security_schemes,
        endpoints=endpoints,
        schemas=schemas,
        metadata={"spec_version": version, "source_url": source_url},
    )
