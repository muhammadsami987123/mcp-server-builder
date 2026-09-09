"""Top-level API discovery pipeline: turns a user-supplied URL into a DiscoveryResult.

Never fabricates a discovery — if nothing machine-readable or documentation-shaped
is found, returns success=False with a clear reason.
"""

from __future__ import annotations

import json
from urllib.parse import urljoin, urlparse

import yaml
from bs4 import BeautifulSoup

from app import config
from app.models.api import DiscoveryResult, SpecType
from app.services.url_fetcher import FetchResult, SSRFError, safe_fetch, validate_url_format


def _looks_like_spec(doc: object) -> bool:
    return isinstance(doc, dict) and ("openapi" in doc or "swagger" in doc) and "paths" in doc


def _try_parse_spec_text(text: str, content_type: str) -> tuple[dict, str] | None:
    """Attempts to parse text as an OpenAPI/Swagger doc. Returns (doc, format) or None."""
    text = (text or "").strip()
    if not text:
        return None

    if "json" in content_type or text.startswith("{"):
        try:
            doc = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            doc = None
        else:
            if _looks_like_spec(doc):
                return doc, "json"

    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        doc = None
    if _looks_like_spec(doc):
        return doc, "yaml"

    return None


def _extract_candidate_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for tag in soup.find_all(["a", "link"]):
        href = tag.get("href")
        if not href:
            continue
        href_lower = href.lower()
        link_text = tag.get_text(" ", strip=True).lower() if tag.name == "a" else ""

        is_spec_file = href_lower.endswith((".json", ".yaml", ".yml"))
        matches_keyword = any(kw in href_lower or kw in link_text for kw in config.DOC_LINK_KEYWORDS)
        if not (is_spec_file or matches_keyword):
            continue

        absolute = urljoin(base_url, href)
        if not absolute.startswith(("http://", "https://")) or absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)

    links.sort(key=lambda u: 0 if u.lower().endswith((".json", ".yaml", ".yml")) else 1)
    return links


def _spec_result(url: str, doc: dict, fmt: str, pages: list[str]) -> DiscoveryResult:
    spec_type = SpecType.SWAGGER if "swagger" in doc else SpecType.OPENAPI
    return DiscoveryResult(
        source_url=url,
        spec_type=spec_type,
        spec_format=fmt,
        raw_spec=doc,
        discovered_pages=pages,
        success=True,
    )


async def discover_api(url: str) -> DiscoveryResult:
    ok, reason = validate_url_format(url)
    if not ok:
        return DiscoveryResult(
            source_url=url, spec_type=SpecType.NONE, success=False, error_message=reason
        )

    discovered_pages: list[str] = []

    try:
        initial: FetchResult = await safe_fetch(url)
    except SSRFError as e:
        return DiscoveryResult(source_url=url, spec_type=SpecType.NONE, success=False, error_message=str(e))
    except Exception as e:  # noqa: BLE001 - network fetch is inherently unpredictable
        return DiscoveryResult(
            source_url=url, spec_type=SpecType.NONE, success=False, error_message=f"Could not fetch URL: {e}"
        )

    discovered_pages.append(initial.url)

    direct = _try_parse_spec_text(initial.text, initial.content_type)
    if direct is not None:
        doc, fmt = direct
        return _spec_result(url, doc, fmt, discovered_pages)

    parsed = urlparse(initial.url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    for candidate_path in config.OPENAPI_CANDIDATE_PATHS:
        if len(discovered_pages) >= config.MAX_DISCOVERY_PAGES:
            break
        candidate_url = origin + candidate_path
        try:
            candidate_result = await safe_fetch(candidate_url)
        except SSRFError:
            continue
        except Exception:  # noqa: BLE001
            continue

        discovered_pages.append(candidate_result.url)
        candidate_doc = _try_parse_spec_text(candidate_result.text, candidate_result.content_type)
        if candidate_doc is not None:
            doc, fmt = candidate_doc
            return _spec_result(url, doc, fmt, discovered_pages)

    is_html = "html" in initial.content_type or initial.text.lstrip().startswith("<")
    if is_html:
        soup = BeautifulSoup(initial.text, "html.parser")
        for link in _extract_candidate_links(soup, initial.url):
            if len(discovered_pages) >= config.MAX_DISCOVERY_PAGES:
                break
            try:
                link_result = await safe_fetch(link)
            except SSRFError:
                continue
            except Exception:  # noqa: BLE001
                continue

            discovered_pages.append(link_result.url)
            link_doc = _try_parse_spec_text(link_result.text, link_result.content_type)
            if link_doc is not None:
                doc, fmt = link_doc
                return _spec_result(url, doc, fmt, discovered_pages)

        return DiscoveryResult(
            source_url=url,
            spec_type=SpecType.HTML_DOCS,
            spec_format="html",
            raw_spec={"html": initial.text},
            discovered_pages=discovered_pages,
            success=True,
        )

    return DiscoveryResult(
        source_url=url,
        spec_type=SpecType.NONE,
        success=False,
        error_message=(
            "No OpenAPI/Swagger specification or recognizable API documentation "
            "could be found at this URL or its common spec paths."
        ),
    )
