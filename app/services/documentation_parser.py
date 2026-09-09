"""Best-effort extraction of API endpoints from rendered HTML documentation pages."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.models.api import APIRepresentation, Endpoint, HttpMethod

_METHOD_PATTERN = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/[A-Za-z0-9_\-./{}:]*)")


def _slugify_path(path: str) -> str:
    slug = path.strip("/").replace("{", "").replace("}", "")
    slug = slug.replace("/", "_").replace("-", "_")
    return slug or "root"


def parse_html_documentation(html: str, source_url: str) -> APIRepresentation:
    """Extracts `METHOD /path` patterns and nearby description text from rendered
    API docs. Never fabricates endpoints — returns an empty endpoint list if
    nothing recognizable is found; the caller treats that as discovery failure."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text("\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    found: dict[tuple[str, str], Endpoint] = {}
    for idx, line in enumerate(lines):
        for match in _METHOD_PATTERN.finditer(line):
            method_str, raw_path = match.group(1), match.group(2)
            path = raw_path.rstrip(".,;:)")
            if not path or path == "/":
                continue

            try:
                method = HttpMethod(method_str)
            except ValueError:
                continue

            key = (method.value, path)
            if key in found:
                continue

            trailing = line[match.end():].strip(" -–—:")
            description = trailing or (lines[idx + 1][:300] if idx + 1 < len(lines) else "")

            has_path_param = "{" in path or bool(re.search(r"/:[A-Za-z0-9_]+", path))
            destructive = method == HttpMethod.DELETE or (
                method in (HttpMethod.PUT, HttpMethod.PATCH) and has_path_param
            )

            found[key] = Endpoint(
                path=path,
                method=method,
                operation_id=f"{method.value.lower()}_{_slugify_path(path)}",
                summary=description[:120],
                description=description,
                destructive=destructive,
                source_ref=f"html_docs:{method.value}:{path}",
            )

    parsed_source = urlparse(source_url)
    origin = f"{parsed_source.scheme}://{parsed_source.netloc}" if parsed_source.netloc else source_url
    title_tag = soup.find("title")
    name = title_tag.get_text(strip=True) if title_tag else (parsed_source.netloc or "Discovered API")

    return APIRepresentation(
        name=name,
        description="",
        base_url=origin,
        version="unknown",
        servers=[origin],
        authentication=[],
        endpoints=list(found.values()),
        schemas={},
        metadata={"spec_version": "html_docs", "source_url": source_url},
    )
