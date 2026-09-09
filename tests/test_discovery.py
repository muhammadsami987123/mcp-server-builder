"""Tests for app.services.api_discovery.discover_api and
app.services.openapi_parser.parse_openapi, using respx to mock every httpx
call (never hit the real network) and demo_openapi.json as the reference
fixture."""

from __future__ import annotations

import httpx
import pytest
import respx

from app import config
from app.models.api import HttpMethod, SpecType
from app.services.api_discovery import discover_api
from app.services.openapi_parser import parse_openapi

SWAGGER2_SPEC = {
    "swagger": "2.0",
    "info": {"title": "Legacy Pet Store", "version": "1.0"},
    "basePath": "/v2",
    "host": "legacy.example.com",
    "schemes": ["https"],
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List pets",
                "responses": {"200": {"description": "ok"}},
            }
        }
    },
}

HTML_DOCS_PAGE = """
<html><body>
<h1>Widget API Reference</h1>
<p>GET /widgets - List all widgets.</p>
<p>POST /widgets - Create a widget.</p>
</body></html>
"""

PLAIN_HTML_PAGE = "<html><body><h1>Nothing here</h1></body></html>"


def _mock_all_candidates_404(mock, origin: str) -> None:
    for path in config.OPENAPI_CANDIDATE_PATHS:
        mock.get(origin + path).mock(return_value=httpx.Response(404))


class TestDiscoverApiOpenAPI:
    async def test_finds_openapi_at_candidate_path(self, fake_public_dns, demo_spec):
        origin = "https://api.example.com"
        with respx.mock(assert_all_called=False) as mock:
            mock.get(origin + "/openapi.json").mock(
                return_value=httpx.Response(
                    200, headers={"content-type": "application/json"}, json=demo_spec
                )
            )
            mock.route(host="api.example.com").mock(return_value=httpx.Response(404))

            result = await discover_api(origin + "/")

        assert result.success is True
        assert result.spec_type == SpecType.OPENAPI
        assert result.raw_spec is not None
        assert result.raw_spec.get("info", {}).get("title") == "Task Manager API"


class TestDiscoverApiSwagger2:
    async def test_finds_swagger2(self, fake_public_dns):
        origin = "https://legacy.example.com"
        with respx.mock(assert_all_called=False) as mock:
            mock.get(origin + "/swagger.json").mock(
                return_value=httpx.Response(
                    200, headers={"content-type": "application/json"}, json=SWAGGER2_SPEC
                )
            )
            mock.route(host="legacy.example.com").mock(return_value=httpx.Response(404))

            result = await discover_api(origin + "/")

        assert result.success is True
        assert result.spec_type == SpecType.SWAGGER
        assert result.raw_spec is not None
        assert result.raw_spec.get("swagger") == "2.0"


class TestDiscoverApiHtmlFallback:
    async def test_falls_back_to_html_docs_parsing(self, fake_public_dns):
        origin = "https://docs.example.com"
        with respx.mock(assert_all_called=False) as mock:
            mock.get(origin + "/").mock(
                return_value=httpx.Response(
                    200, headers={"content-type": "text/html"}, text=HTML_DOCS_PAGE
                )
            )
            mock.route(host="docs.example.com").mock(return_value=httpx.Response(404))

            result = await discover_api(origin + "/")

        assert result.spec_type == SpecType.HTML_DOCS
        assert result.success is True


class TestDiscoverApiNoApiFound:
    async def test_returns_failure_for_unreachable_site(self, fake_public_dns):
        origin = "https://notanapi.example.com"
        with respx.mock(assert_all_called=False) as mock:
            mock.route(host="notanapi.example.com").mock(return_value=httpx.Response(404))

            result = await discover_api(origin + "/")

        assert result.success is False
        assert result.spec_type == SpecType.NONE
        assert result.error_message


class TestParseOpenapiDemoSpec:
    def test_produces_exactly_8_endpoints(self, demo_spec):
        api = parse_openapi(demo_spec, "https://api.demo-taskmanager.dev/v1")
        assert len(api.endpoints) == 8

    def test_methods_and_paths_match_fixture(self, demo_spec):
        api = parse_openapi(demo_spec, "https://api.demo-taskmanager.dev/v1")
        pairs = {(e.method, e.path) for e in api.endpoints}
        expected = {
            (HttpMethod.GET, "/tasks"),
            (HttpMethod.POST, "/tasks"),
            (HttpMethod.GET, "/tasks/{id}"),
            (HttpMethod.PATCH, "/tasks/{id}"),
            (HttpMethod.DELETE, "/tasks/{id}"),
            (HttpMethod.GET, "/projects"),
            (HttpMethod.POST, "/projects"),
            (HttpMethod.DELETE, "/projects/{id}"),
        }
        assert pairs == expected

    def test_destructive_flags(self, demo_spec):
        api = parse_openapi(demo_spec, "https://api.demo-taskmanager.dev/v1")
        by_ref = {(e.method, e.path): e for e in api.endpoints}

        assert by_ref[(HttpMethod.DELETE, "/tasks/{id}")].destructive is True
        assert by_ref[(HttpMethod.DELETE, "/projects/{id}")].destructive is True
        assert by_ref[(HttpMethod.PATCH, "/tasks/{id}")].destructive is True

        assert by_ref[(HttpMethod.GET, "/tasks")].destructive is False
        assert by_ref[(HttpMethod.POST, "/tasks")].destructive is False
        assert by_ref[(HttpMethod.GET, "/tasks/{id}")].destructive is False
        assert by_ref[(HttpMethod.GET, "/projects")].destructive is False
        assert by_ref[(HttpMethod.POST, "/projects")].destructive is False
