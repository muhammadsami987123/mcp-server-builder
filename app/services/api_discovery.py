"""API discovery service - detects OpenAPI specs and API documentation."""
import asyncio
from typing import Optional
from urllib.parse import urljoin, urlparse

from app.config import DOCS_PATHS, MAX_DISCOVERY_PAGES, OPENAPI_PATHS
from app.models.api import APIRepresentation, DiscoveryResult
from app.services.openapi_parser import OpenAPIParser
from app.services.url_fetcher import SSRFException, URLFetcher


class APIDiscovery:
    """Discover and detect APIs from URLs."""

    @staticmethod
    async def discover(url: str) -> DiscoveryResult:
        """
        Discover API from URL by trying common OpenAPI/Swagger paths.

        Args:
            url: Base URL to discover from

        Returns:
            DiscoveryResult with discovered API info or errors
        """
        errors = []
        warnings = []

        # Normalize base URL
        base_url = url.rstrip("/")

        # Try OpenAPI/Swagger paths
        api, detected_type, raw_spec, discovery_errors = await APIDiscovery._try_openapi_paths(
            base_url
        )

        if api:
            return DiscoveryResult(
                success=True,
                api=api,
                raw_spec=raw_spec,
                detected_type=detected_type,
                errors=errors,
                warnings=warnings,
            )

        errors.extend(discovery_errors)

        # Try documentation paths
        api, doc_errors = await APIDiscovery._try_documentation_paths(base_url)

        if api:
            return DiscoveryResult(
                success=True,
                api=api,
                raw_spec=None,
                detected_type="html_docs",
                errors=errors,
                warnings=warnings,
            )

        errors.extend(doc_errors)

        return DiscoveryResult(
            success=False,
            api=None,
            raw_spec=None,
            detected_type=None,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    async def _try_openapi_paths(
        base_url: str,
    ) -> tuple[Optional[APIRepresentation], Optional[str], Optional[dict], list]:
        """Try common OpenAPI/Swagger specification paths."""
        errors = []
        fetcher = URLFetcher()

        for path in OPENAPI_PATHS[:MAX_DISCOVERY_PAGES]:
            url = urljoin(base_url, path)

            try:
                content = await fetcher.fetch(url)

                # Try to detect and parse
                if "{" in content or content.startswith("---"):
                    # Likely JSON or YAML
                    spec_type = "yaml" if content.startswith("---") else "json"
                    success, api, raw_spec, parse_errors = OpenAPIParser.parse_spec(
                        content, spec_type, base_url
                    )

                    if success and api:
                        detected_type = "openapi3" if spec_type == "json" else "swagger2"
                        return api, detected_type, raw_spec, []

                    errors.extend(parse_errors)

            except SSRFException as e:
                errors.append(f"SSRF blocked access to {url}: {str(e)}")
            except Exception as e:
                errors.append(f"Error fetching {url}: {str(e)}")

        return None, None, None, errors

    @staticmethod
    async def _try_documentation_paths(
        base_url: str,
    ) -> tuple[Optional[APIRepresentation], list]:
        """Try common documentation paths and extract API info from HTML."""
        errors = []
        fetcher = URLFetcher()

        for path in DOCS_PATHS[:3]:
            url = urljoin(base_url, path)

            try:
                content = await fetcher.fetch(url)

                # For now, we look for JSON embedded in HTML
                # (Swagger UI, ReDoc, etc. typically embed spec in window.spec)
                api = APIDiscovery._extract_api_from_html(content, base_url)
                if api:
                    return api, []

            except SSRFException as e:
                errors.append(f"SSRF blocked access to {url}: {str(e)}")
            except Exception as e:
                errors.append(f"Error fetching {url}: {str(e)}")

        return None, errors

    @staticmethod
    def _extract_api_from_html(html_content: str, base_url: str) -> Optional[APIRepresentation]:
        """
        Try to extract OpenAPI spec from HTML (e.g., Swagger UI).
        Look for window.spec, SwaggerUIBundle config, etc.
        """
        # Look for common patterns in HTML-based API documentation
        import re
        import json

        # Pattern 1: window.spec = {...}
        match = re.search(r'window\.spec\s*=\s*({.*?});', html_content, re.DOTALL)
        if match:
            try:
                spec_json = match.group(1)
                spec = json.loads(spec_json)
                success, api, _, _ = OpenAPIParser.parse_spec(json.dumps(spec), "json", base_url)
                if success and api:
                    return api
            except Exception:
                pass

        # Pattern 2: SwaggerUIBundle config
        match = re.search(r'url:\s*["\']([^"\']+\.json)["\']', html_content)
        if match:
            # This would require another fetch, skip for now
            pass

        return None
