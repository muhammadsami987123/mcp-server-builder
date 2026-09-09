# AGENTS.md – Instructions for AI Coding Agents

This document is for AI agents (Claude Code, other LLMs, and human-directed coding assistants)
working in the MCP Server Builder codebase. It reflects the actual, current implementation
contract in `docs/superpowers/plans/2026-09-07-mcp-server-builder-contract.md` — read that file
first for exact function signatures if you're modifying a service.

## What this project is

MCP Server Builder turns an API/documentation URL into a complete, runnable MCP (Model Context
Protocol) server. Pipeline:

```
URL → discover → analyze → design-tools (AI) → generate → validate → download
```

**Built by**: Muhammad Sami Asghar Mughal (Senior AI Agent Engineer, COO at MARSA Empower).

## Architecture at a glance

```
Frontend (Jinja2 templates + Tailwind CDN + vanilla JS)
         ↓  fetch() calls to /api/*
FastAPI Backend (app/main.py + app/routes/*)
    ├─ URL Validation & SSRF Protection      (app/services/url_fetcher.py)
    ├─ API Discovery                          (app/services/api_discovery.py)
    ├─ OpenAPI/Swagger Parsing                (app/services/openapi_parser.py)
    ├─ HTML Documentation Parsing             (app/services/documentation_parser.py)
    ├─ API Normalization/Analysis             (app/services/api_analyzer.py)
    ├─ OpenAI Access (centralized)            (app/services/openai_service.py)
    ├─ AI-Driven MCP Tool Design              (app/services/mcp_designer.py)
    ├─ Code Generation (Jinja2)               (app/services/mcp_generator.py, app/templates/mcp_project/*.jinja)
    ├─ Generated-Server Validation            (app/services/validator.py)
    └─ Project Storage (JSON files + zips)    (app/services/project_store.py)
         ↓
Generated MCP Servers (complete, runnable Python projects under generated-projects/{id}/)
```

## Repository layout (`app/`)

```
app/
├── main.py                      # FastAPI app, CORS, static mount, routers, /health
├── config.py                    # env vars, SSRF blocklists, thresholds, paths
├── models/
│   ├── api.py                   # APIRepresentation, Endpoint, Parameter, SecurityScheme, DiscoveryResult, enums
│   ├── mcp.py                   # MCPTool, MCPServerDesign, GeneratedMCPServer, ValidationResult, MCPProject
│   └── project.py               # ProjectMetadata, ProjectSummary, HistoryResponse
├── services/
│   ├── url_fetcher.py           # SSRF-safe fetch — safe_fetch(), validate_url_format()
│   ├── api_discovery.py         # discover_api(url) -> DiscoveryResult
│   ├── openapi_parser.py        # parse_openapi(), detect_spec_version()
│   ├── documentation_parser.py  # parse_html_documentation() — best-effort HTML extraction
│   ├── api_analyzer.py          # normalize_api(), detect_authentication(), summarize_for_ai()
│   ├── openai_service.py        # call_structured() — the ONLY file that imports `openai`
│   ├── mcp_designer.py          # design_tools(), build_demo_design()
│   ├── mcp_generator.py         # generate_server(), render_mcp_client_config(), render_readme()
│   ├── validator.py             # validate_generated_server()
│   └── project_store.py         # create/save/load/list/delete_project, build_zip()
├── routes/
│   ├── pages.py                 # GET /, /builder, /history, /project/{id}
│   ├── analysis.py              # POST /api/discover, /api/analyze, /api/design-tools
│   ├── generation.py            # POST /api/generate, /api/validate, /api/regenerate
│   ├── projects.py              # GET/DELETE /api/project/{id}, /api/history, feedback
│   └── downloads.py             # GET /api/project/{id}/download, /api/project/{id}/file
├── templates/                   # Jinja2 page templates + mcp_project/*.jinja code-gen templates
├── static/
│   ├── js/                      # app.js, builder.js, history.js, project.js
│   ├── css/styles.css
│   ├── robots.txt, sitemap.xml
└── data/
    ├── demo_openapi.json        # fixture "Task Manager API" (8 endpoints, bearer auth) for Demo Mode/tests
    └── projects/                # one JSON file per MCPProject, {project_id}.json

generated-projects/              # generated server files + zips live here, NOT in app/data
tests/                           # pytest suite (see docs/TESTING.md)
```

## How to run

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # add OPENAI_API_KEY (optional — Demo Mode works without it)
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

## How to test

```bash
pytest                # full suite (respx-mocked HTTP, no real network calls, no real OpenAI calls)
pytest --cov=app       # with coverage
pytest tests/test_security.py -v
```

See `docs/TESTING.md` for what each test file covers.

## Critical rules for anyone editing this codebase

1. **SSRF protection lives in one place.** All outbound HTTP fetches of user-supplied URLs MUST
   go through `app/services/url_fetcher.py::safe_fetch()`. Never call `httpx.get`/`requests.get`
   directly on user input anywhere else. It resolves hostnames via `socket.getaddrinfo` and
   rejects any resolved address in `config.BLOCKED_NETWORKS` (DNS-rebinding safe), disables
   httpx's automatic redirects and manually re-validates every hop, caps response size, and
   restricts `Content-Type`. See `docs/SECURITY.md` for the full threat model.

2. **OpenAI access is centralized.** `app/services/openai_service.py` is the ONLY file in the
   codebase that imports the `openai` package. All AI calls go through
   `call_structured(system_prompt, user_prompt, response_model)`, which returns a validated
   Pydantic model or raises `OpenAIServiceError` — never a raw SDK exception.

3. **Anti-hallucination rule — every MCP tool must trace to a real endpoint.** `mcp_designer.py`
   asks the model to propose tools, but it never trusts the model's `method`/`path` verbatim:
   every proposed tool is cross-validated against `api.endpoints` by `(method.upper(), path)`.
   If there's no match, the tool is dropped and recorded in `ignored_endpoints` — it is never
   silently invented. The same discipline applies everywhere else in the pipeline: never
   fabricate endpoints, parameters, or auth schemes that weren't actually discovered. If
   something can't be verified, mark it unknown or omit it.

4. **Never log or embed secrets.** API keys/tokens are never logged, and generated MCP servers
   read credentials from environment variables only — never hardcoded.

5. **No comments explaining *what* code does** — only non-obvious *why* comments, sparingly.

6. **Async I/O throughout the request path** — `httpx.AsyncClient`, `async def` routes/services.

7. **Never leak internals to clients.** Routes catch service exceptions and return a clean
   `detail` message with an appropriate status code; a global exception handler in `app/main.py`
   turns any uncaught exception into `{"detail": "Internal error"}` while logging the real
   traceback server-side.

## Storage model

Projects are JSON files, not a database: `config.PROJECTS_DIR / f"{project_id}.json"`, one file
per `MCPProject` (`model_dump(mode="json")`). Generated server files are written to
`config.GENERATED_DIR / project_id / <relative path>`, and downloads are built as a fresh zip
per request (`project_store.build_zip`). Nothing is kept in memory between requests — every route
loads/saves through `project_store`.

## Where to look for more detail

- `docs/ARCHITECTURE.md` — per-service responsibilities and the full request/response flow.
- `docs/SECURITY.md` — SSRF threat model in depth.
- `docs/DEPLOYMENT.md` — dev vs. prod run commands, required env vars.
- `docs/TESTING.md` — test suite layout and how to add coverage.
- `docs/superpowers/plans/2026-09-07-mcp-server-builder-contract.md` — the authoritative
  interface contract (exact function signatures) for this build.
