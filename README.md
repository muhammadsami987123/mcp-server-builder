# MCP Server Builder

**Paste an API or documentation URL. Get back a complete, runnable MCP server.**

MCP Server Builder is an AI-powered platform that discovers and understands an API from a single
URL, uses OpenAI (`gpt-4.1-mini`) to design a clean set of MCP (Model Context Protocol) tools for
it, generates a real, runnable Python MCP server project, validates the generated code, and lets
you browse and download it.

This is not an API documentation viewer and not a generic AI code generator — the whole point is
the pipeline: **discover → understand → design → generate → validate → run.**

## The pipeline

```
URL
 │
 ▼
1. Discover   — fetch the URL safely, detect OpenAPI/Swagger/HTML docs, follow doc links
 │               app/services/url_fetcher.py, api_discovery.py
 ▼
2. Analyze    — parse into a normalized APIRepresentation (endpoints, params, auth)
 │               openapi_parser.py, documentation_parser.py, api_analyzer.py
 ▼
3. Design     — OpenAI designs MCP tools; every tool is cross-validated against a real
 │               discovered endpoint before being trusted (never fabricated)
 │               openai_service.py, mcp_designer.py
 ▼
4. Generate   — render a complete Python MCP server project from Jinja2 templates
 │               mcp_generator.py, app/templates/mcp_project/*.jinja
 ▼
5. Validate   — syntax-check every generated file, verify MCP server/tool structure
 │               validator.py
 ▼
6. Download   — browse the project in the UI, download a ZIP, run it locally
                 project_store.py
```

## Architecture

```
Browser
  │  Jinja2-rendered pages (index / builder / history / project) + vanilla JS + Tailwind CDN
  ▼
FastAPI app  (app/main.py)
  │
  ├─ app/routes/pages.py        GET  /, /builder, /history, /project/{id}
  ├─ app/routes/analysis.py     POST /api/discover, /api/analyze, /api/design-tools
  ├─ app/routes/generation.py   POST /api/generate, /api/validate, /api/regenerate
  ├─ app/routes/projects.py     GET/DELETE /api/project/{id}, /api/history, feedback
  └─ app/routes/downloads.py    GET  /api/project/{id}/download, /api/project/{id}/file
  │
  ▼
app/services/
  ├─ url_fetcher.py          SSRF-safe fetch (the only way user URLs get requested)
  ├─ api_discovery.py        finds OpenAPI/Swagger/HTML docs
  ├─ openapi_parser.py       OpenAPI 3.x / Swagger 2.0 -> APIRepresentation
  ├─ documentation_parser.py best-effort HTML docs -> APIRepresentation
  ├─ api_analyzer.py         normalize, dedupe, summarize for the AI prompt
  ├─ openai_service.py       centralized OpenAI access (only file importing `openai`)
  ├─ mcp_designer.py         AI tool design + anti-hallucination cross-validation
  ├─ mcp_generator.py        Jinja2 code generation -> GeneratedMCPServer
  ├─ validator.py            syntax + structural validation of generated code
  └─ project_store.py        JSON-file project storage, on-disk files, ZIP builder
  │
  ▼
app/data/projects/{id}.json      generated-projects/{id}/...       generated-projects/{id}.zip
(project metadata + state)       (actual generated server files)   (download artifact)
```

## Install & run

```bash
# Clone
git clone <repo-url>
cd mcp-server-builder

# Virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set OPENAI_API_KEY (optional — Demo Mode works without a key)

# Run
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

### Environment variables

From `.env.example`:

```bash
OPENAI_API_KEY=sk-...        # optional; required for real (non-demo) tool design
OPENAI_MODEL=gpt-4.1-mini

HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=*

REQUEST_TIMEOUT=20
MAX_RESPONSE_SIZE=10485760     # 10MB
MAX_DISCOVERY_PAGES=10
MAX_REDIRECTS=5
```

## Try it without an API key

Demo Mode runs the full pipeline against a built-in fixture ("Task Manager API", 8 endpoints,
bearer auth — `app/data/demo_openapi.json`) using a hand-written `MCPServerDesign` instead of a
live OpenAI call, so you can see a complete generated server with zero configuration.

## Routes

### Pages

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Marketing/home page |
| GET | `/builder` | Core builder app |
| GET | `/history` | Project history |
| GET | `/project/{id}` | Project detail / explorer |

### API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/discover` | `{url}` → discover API docs at a URL |
| POST | `/api/analyze` | `{project_id}` → normalize discovery into an `APIRepresentation` |
| POST | `/api/design-tools` | `{project_id, demo}` → AI-designed `MCPServerDesign` |
| POST | `/api/generate` | `{project_id, preferences}` → generate + validate the server |
| POST | `/api/validate` | `{project_id}` → re-run validation |
| POST | `/api/regenerate` | `{project_id, preferences}` → regenerate without re-discovery |
| GET | `/api/project/{id}` | Full `MCPProject` |
| GET | `/api/project/{id}/files` | Generated files |
| GET | `/api/project/{id}/tools` | Designed tools |
| GET | `/api/history` | Project history list |
| DELETE | `/api/project/{id}` | Delete a project |
| POST | `/api/project/{id}/feedback` | `{rating, comment}` |
| GET | `/api/project/{id}/download` | Download the project as a ZIP |
| GET | `/api/project/{id}/file?path=` | Read one generated file's content |
| GET | `/health` | Health check |

Every route loads/saves state through `app/services/project_store.py` — nothing is kept in
memory between requests.

## Security model

All outbound fetches of user-supplied URLs go through `app/services/url_fetcher.py`, which:

- resolves the hostname via `socket.getaddrinfo` and rejects the request if **any** resolved
  address falls inside a private/loopback/link-local/reserved network (DNS-rebinding safe);
- blocks a hostname denylist (`localhost`, cloud metadata endpoints, etc.);
- disables httpx's automatic redirects and manually re-validates the host/IP of every redirect
  hop before following it, up to a configured maximum;
- streams the response body and aborts once it exceeds a hard size cap;
- restricts `Content-Type` to an explicit allowlist;
- never executes fetched JavaScript or HTML.

Generated MCP servers read credentials from environment variables only — secrets are never
embedded in generated code or logged. See `docs/SECURITY.md` for the full threat model.

## Testing

```bash
pytest                 # full suite
pytest --cov=app        # with coverage
pytest tests/test_security.py -v
```

See `docs/TESTING.md` for what each test file covers and how to add new coverage.

## Limitations

- **HTML-docs parsing is best-effort.** When an API has no machine-readable OpenAPI/Swagger spec,
  `documentation_parser.py` uses regex/heuristic extraction over rendered HTML docs. It will
  under-discover endpoints on unusual doc layouts, and it never fabricates endpoints to
  compensate — a poor extraction just means fewer discovered endpoints, not wrong ones.
- **OAuth2 needs manual credentials.** The generated server never obtains OAuth2 tokens on its
  own; you supply a token/credentials via environment variables.
- **JSON-file storage is not built for scale.** Projects are stored as individual JSON files
  under `app/data/projects/`; this is fine for personal/small-team use but isn't a substitute for
  a real database at high project counts or concurrency.
- **One API per generated server.** Multi-API composition into a single MCP server isn't
  supported.

## Project structure

See `AGENTS.md` for the full annotated `app/` layout, and `docs/ARCHITECTURE.md` for a
per-service breakdown.

## License

MIT — see `LICENSE`.
