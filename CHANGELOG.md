# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0]

Initial ground-up rebuild of MCP Server Builder after the previous implementation was lost.
Built as a parallel multi-agent effort against a shared implementation contract
(`docs/superpowers/plans/2026-09-07-mcp-server-builder-contract.md`).

### Added

- Full pipeline: URL discovery → API analysis → AI-driven MCP tool design → Jinja2-based server
  code generation → generated-code validation → project storage → ZIP download.
- SSRF-safe URL fetching (`app/services/url_fetcher.py`) — DNS-rebinding-safe address resolution,
  manually re-validated redirects, response size cap, content-type restriction.
- OpenAPI 3.x and Swagger 2.0 parsing (`app/services/openapi_parser.py`), plus best-effort HTML
  documentation parsing (`app/services/documentation_parser.py`) as a fallback discovery path.
- Centralized OpenAI access (`app/services/openai_service.py`) with structured-output validation
  and retry-with-correction, and AI-driven MCP tool design
  (`app/services/mcp_designer.py`) that cross-validates every proposed tool against a real
  discovered endpoint before trusting it (anti-hallucination guarantee).
- Jinja2-templated MCP server code generation (`app/services/mcp_generator.py`) producing a
  complete, runnable Python project (`FastMCP`-based server, typed tool input models, shared
  async HTTP client, generated tests and README).
- Generated-server validation (`app/services/validator.py`) — syntax checks via `ast.parse`,
  structural checks on the MCP server and tool schemas.
- JSON-file project storage and ZIP packaging (`app/services/project_store.py`) — no database.
- FastAPI routes for pages, discovery/analysis, generation/validation, project management, and
  downloads (`app/routes/*`), with a global exception handler that never leaks internals.
- Built-in Demo Mode using a bundled fixture API (`app/data/demo_openapi.json`, "Task Manager
  API", 8 endpoints, bearer auth) so the full pipeline is explorable with zero OpenAI API key.
- Light-theme, developer-SaaS frontend (Jinja2 templates + Tailwind CDN + vanilla JS) with a
  real, staged progress experience during generation rather than a fake progress bar.
- `pytest` suite covering SSRF protection, discovery/parsing, AI tool design cross-validation,
  code generation, and generated-code validation, with `respx`-mocked HTTP and mocked OpenAI
  calls (no real network or API access from tests).
- Project documentation: `README.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`,
  `docs/DEPLOYMENT.md`, `docs/TESTING.md`, `docs/CONTRIBUTING.md`.
