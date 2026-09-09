# Architecture

This document explains what each backend service is responsible for, the `MCPProject` storage
model, and the end-to-end request/response flow for a single generation. It complements
`AGENTS.md` (repo layout) and `docs/SECURITY.md` (SSRF details).

## Services

### `app/services/url_fetcher.py`

The single choke point for every outbound HTTP fetch of a user-supplied URL. Exposes
`validate_url_format()` for cheap structural checks (scheme, hostname, length, blocked-hostname
denylist) and `safe_fetch()`, which resolves the hostname via `socket.getaddrinfo`, rejects it if
any resolved address falls inside a blocked network, disables httpx's automatic redirect
following so every hop can be re-validated by hand, streams the response body with a hard size
cap, and restricts `Content-Type` to an allowlist. No other file in the codebase is permitted to
make a raw HTTP request against user input.

### `app/services/api_discovery.py`

Owns the "where is the API spec" problem. Given a URL, it tries — in order — treating the URL
itself as a spec, probing well-known OpenAPI/Swagger candidate paths under the same origin,
crawling HTML for links that look like docs/spec references (bounded by
`config.MAX_DISCOVERY_PAGES`), and finally falling back to returning the raw HTML for
documentation-parser handling. If nothing usable is found at all, it returns a `DiscoveryResult`
with `success=False` and a clear `error_message` rather than guessing.

### `app/services/openapi_parser.py`

Parses a raw OpenAPI 3.x or Swagger 2.0 document (once discovery has found one) into the
normalized `APIRepresentation` model: servers/`basePath`, every operation on every path,
path/query/header/cookie parameters, request bodies, responses, tags, security requirements, and
a synthesized `operationId` when the spec omits one. It also flags `destructive=True` on DELETE
and on PUT/PATCH against a path with a path parameter, and stamps each `Endpoint.source_ref` (for
example `openapi:get:/tasks`) so later stages can prove provenance.

### `app/services/documentation_parser.py`

The fallback path when no machine-readable spec exists. Does best-effort regex/BeautifulSoup
extraction of `METHOD /path` patterns and their surrounding description text out of rendered HTML
documentation. Every endpoint it finds is stamped with `source_ref="html_docs:{method}:{path}"`.
Critically, it never invents endpoints to fill gaps — if nothing recognizable is found, it returns
an `APIRepresentation` with an empty endpoint list, and the caller (`api_analyzer.normalize_api`)
is the one that decides an empty result means discovery failed.

### `app/services/api_analyzer.py`

The normalization layer between discovery/parsing and everything downstream. `normalize_api()`
dispatches on `DiscoveryResult.spec_type` to the right parser, dedupes endpoints by
`(method, path)`, and raises if discovery itself failed. `summarize_for_ai()` produces the compact,
token-bounded JSON payload that actually gets sent to OpenAI — endpoint method/path/summary/typed
params only, truncated schemas, grouped by tag — deliberately never the raw spec, to keep prompts
small and to avoid leaking anything beyond what's needed for tool design.

### `app/services/openai_service.py`

The only file in the codebase that imports the `openai` package. Exposes
`call_structured(system_prompt, user_prompt, response_model)`, which calls
`AsyncOpenAI` with `response_format={"type": "json_object"}`, parses the JSON, and validates it
against the given Pydantic model. On a JSON or schema validation failure it retries with a
corrective follow-up message that includes the actual validation error, up to `retries` times,
and raises a clean `OpenAIServiceError` (never a raw SDK exception, never leaking the prompt or
key) if it still can't produce a valid response.

### `app/services/mcp_designer.py`

Turns an `APIRepresentation` into an `MCPServerDesign`. Builds a system prompt describing the
tool-design task, sends `api_analyzer.summarize_for_ai(api)` through `openai_service`, and then
— this is the anti-hallucination step — cross-validates every proposed tool against
`api.endpoints` by `(method.upper(), path)`. Anything the model proposed that doesn't match a real
endpoint is dropped and recorded in `ignored_endpoints` instead of being trusted. `destructive` is
copied from the matched `Endpoint`, never re-derived from the model's output. `build_demo_design()`
provides a fixed, hand-written design for the bundled demo spec so Demo Mode works with zero
OpenAI key configured.

### `app/services/mcp_generator.py`

Renders the actual MCP server project from Jinja2 templates under `app/templates/mcp_project/`.
Applies `GenerationPreferences` first (filtering read-only vs. destructive tools, honoring an
explicit tool selection, grouping tools into modules by resource), then renders `src/server.py`
(the `FastMCP` server, one `@mcp.tool()` per generated tool function), `src/config.py`,
`src/client.py` (shared async httpx client with auth header injection), `src/models.py` (Pydantic
input models per tool), `src/tools/<group>.py`, tests (when requested), `.env.example`,
`requirements.txt`, `README.md` (via `render_readme()`, built from the real tool list — not
boilerplate), and `mcp-config.json` (via `render_mcp_client_config()`). Output is a flat list of
`GeneratedFile` objects, not files written to disk yet.

### `app/services/validator.py`

Runs a fixed set of checks against a `GeneratedMCPServer` and reports each as a
`ValidationCheck`: required files present, every `.py` file's content parses with `ast.parse`
(reporting the exact `SyntaxError` on failure), `src/server.py` actually instantiates an MCP
server and registers at least one tool, every tool has a JSON-Schema-shaped `input_schema`,
`.env.example` covers the env vars `config.py` reads, and `requirements.txt` is non-empty and
includes `mcp`. Only `severity="error"` checks can fail the build (`passed=False`); soft issues
(missing optional test files, OAuth2 needing manual credentials) are `severity="warning"`.

### `app/services/project_store.py`

The persistence layer — plain JSON files, no database. `create_project()`/`save_project()`/
`load_project()`/`list_projects()`/`delete_project()` manage one JSON file per project at
`config.PROJECTS_DIR / f"{project_id}.json"` (`MCPProject.model_dump(mode="json")`).
`save_generated_files_to_disk()` writes each `GeneratedFile` under
`config.GENERATED_DIR / project_id / <file.path>`. `build_zip()` zips that directory fresh on
every call (projects are small enough that caching isn't worth the complexity) and returns the
zip path for download.

## The `MCPProject` storage model

Everything about a single build lives in one `MCPProject` JSON document
(`app/models/mcp.py`):

```
MCPProject
├── id                 uuid4().hex[:12]
├── created_at / updated_at
├── source_url
├── status             pending|discovering|analyzing|designing|generating|validating|ready|failed
├── api                APIRepresentation.model_dump()   (set after /api/analyze)
├── design             MCPServerDesign.model_dump()     (set after /api/design-tools)
├── generated           GeneratedMCPServer.model_dump()  (set after /api/generate)
├── validation          ValidationResult.model_dump()    (set after /api/generate or /api/validate)
├── preferences          GenerationPreferences used for the last generation
└── error_message        set + status="failed" on any service exception
```

Every `/api/*` route loads the project, mutates the relevant field(s) plus `status`, and saves it
back — there is no in-memory session state, so any route can be re-run idempotently against a
project's current stored state (this is exactly what `/api/regenerate` and `/api/validate` rely
on: they operate on `project.api`/`project.design` already on disk, with no re-discovery needed).

## End-to-end flow for one generation

1. **`POST /api/discover {url}`** — `project_store.create_project(url)` creates a new
   `MCPProject` (`status="discovering"`). `api_discovery.discover_api(url)` runs (itself calling
   `url_fetcher.safe_fetch` for every hop). The `DiscoveryResult` and `project_id` are returned;
   nothing is written into `project.api` yet.
2. **`POST /api/analyze {project_id}`** — loads the project, re-runs discovery data through
   `api_analyzer.normalize_api()` to get an `APIRepresentation`, stores it as `project.api`,
   sets `status="analyzing"` → saved, returns `{api}`.
3. **`POST /api/design-tools {project_id, demo}`** — loads `project.api`, calls
   `mcp_designer.design_tools(api)` (or `build_demo_design()` when `demo=True`/no API key),
   stores the result as `project.design`, `status="designing"` → saved, returns `{design}`. The
   frontend pauses here for the user to review/deselect tools.
4. **`POST /api/generate {project_id, preferences}`** — loads `project.api`/`project.design`,
   calls `mcp_generator.generate_server()`, writes the files to disk via
   `project_store.save_generated_files_to_disk()`, runs `validator.validate_generated_server()`,
   stores `generated`/`validation`/`preferences` on the project, sets `status="ready"` (or
   `"failed"` if validation reported errors — the files are still saved so the user can inspect
   what went wrong), saves, and returns `{generated, validation}`.
5. **`GET /api/project/{id}/download`** — `project_store.build_zip(project_id)` zips the
   on-disk generated directory and the route streams it back as a `FileResponse`.

Any service exception at any step is caught by the route, which sets
`project.status="failed"`, `project.error_message=str(e)`, saves, and responds with a clear
`detail` message (400/502 as appropriate) — never a bare 500 with a stack trace. A global
exception handler in `app/main.py` is the last line of defense for anything uncaught.
