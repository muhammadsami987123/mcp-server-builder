"""Normalizes discovery output into APIRepresentation and produces a compact,
token-efficient summary for the AI tool-design step. The raw spec is never
sent to OpenAI — only the output of summarize_for_ai."""

from __future__ import annotations

from typing import Any

from app.models.api import APIRepresentation, DiscoveryResult, Endpoint, SecurityScheme, SpecType
from app.services import openapi_parser
from app.services.documentation_parser import parse_html_documentation


def normalize_api(discovery: DiscoveryResult) -> APIRepresentation:
    if not discovery.success:
        raise ValueError(discovery.error_message or "Discovery did not succeed; nothing to normalize")

    if discovery.spec_type in (SpecType.OPENAPI, SpecType.SWAGGER):
        if not isinstance(discovery.raw_spec, dict):
            raise ValueError("Discovery reported a spec but no raw_spec payload was captured")
        api = openapi_parser.parse_openapi(discovery.raw_spec, discovery.source_url)
    elif discovery.spec_type == SpecType.HTML_DOCS:
        html = ""
        if isinstance(discovery.raw_spec, dict):
            html = discovery.raw_spec.get("html", "")
        api = parse_html_documentation(html, discovery.source_url)
    else:
        raise ValueError("Discovery found no machine-readable spec or documentation to normalize")

    deduped: dict[tuple[str, str], Endpoint] = {}
    for ep in api.endpoints:
        key = (ep.method.value, ep.path)
        if key not in deduped:
            deduped[key] = ep
    api.endpoints = list(deduped.values())

    return api


def detect_authentication(raw_spec: dict) -> list[SecurityScheme]:
    if not isinstance(raw_spec, dict):
        return []
    try:
        return openapi_parser.extract_security_schemes(raw_spec)
    except Exception:  # noqa: BLE001 - best-effort detection, never fatal
        return []


def _compact_parameter(param) -> dict[str, Any]:
    return {
        "name": param.name,
        "in": param.location.value,
        "type": param.type,
        "required": param.required,
    }


def _compact_request_body(ep: Endpoint) -> dict[str, Any] | None:
    rb = ep.request_body
    if rb is None:
        return None
    fields = list((rb.schema_ or {}).get("properties", {}).keys())[:15]
    return {"content_type": rb.content_type, "required": rb.required, "fields": fields}


def _compact_endpoint(ep: Endpoint) -> dict[str, Any]:
    return {
        "method": ep.method.value,
        "path": ep.path,
        "operation_id": ep.operation_id,
        "summary": (ep.summary or ep.description)[:150],
        "destructive": ep.destructive,
        "deprecated": ep.deprecated,
        "parameters": [_compact_parameter(p) for p in ep.parameters],
        "request_body": _compact_request_body(ep),
    }


def summarize_for_ai(api: APIRepresentation, max_endpoints: int = 60) -> dict:
    """Compact JSON-able dict: endpoints grouped by tag with only method/path/
    summary/params-by-name-and-type, truncated schemas. Sized to stay well under
    a few thousand tokens even for large APIs."""
    included = api.endpoints[:max_endpoints]

    endpoints_by_tag: dict[str, list[dict[str, Any]]] = {}
    for ep in included:
        tag = ep.tags[0] if ep.tags else "general"
        endpoints_by_tag.setdefault(tag, []).append(_compact_endpoint(ep))

    return {
        "name": api.name,
        "description": (api.description or "")[:300],
        "base_url": api.base_url,
        "version": api.version,
        "authentication": [
            {
                "type": scheme.type.value,
                "scheme_name": scheme.scheme_name,
                "header_name": scheme.header_name,
            }
            for scheme in api.authentication
        ],
        "total_endpoints": len(api.endpoints),
        "endpoints_included": len(included),
        "truncated": len(api.endpoints) > max_endpoints,
        "endpoints_by_tag": endpoints_by_tag,
    }
