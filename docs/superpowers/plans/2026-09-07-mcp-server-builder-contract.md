# MCP Server Builder — Implementation Contract

> **For agentic workers:** This is the shared interface contract for a parallel, multi-agent build. Each agent owns a fixed set of files. Do NOT edit files outside your assignment — other agents are writing them concurrently. Import only from the Pydantic models below and from the function signatures documented here; they are fixed and will not change.

**Goal:** Build a complete, production-quality AI-powered MCP Server Builder: paste an API/docs URL, discover and analyze the API, use OpenAI (GPT-4.1-mini) to design MCP tools, generate a real runnable MCP server project, validate it, and let the user browse/download it.

**Spec:** `task.md` (repo root) — the full 54-section product spec. This contract translates it into concrete file/function boundaries. When in doubt, `task.md` is the source of truth for product behavior; this file is the source of truth for interfaces.

**Tech stack:** FastAPI + Pydantic + Jinja2 + httpx (backend), vanilla HTML/Tailwind CDN/JS (frontend), OpenAI Python SDK with `gpt-4.1-mini`, local JSON file storage under `app/data/`. No React/Vue/DB/Redis.

## Global constraints (apply to every task)

- Python 3.10+, full type hints on public functions.
- Never trust or fabricate data: every `MCPTool` must trace back to a real discovered `Endpoint` (match on method+path). If something can't be verified, mark it unknown/omit it — never invent endpoints, params, or auth.
- Never log or embed secrets (API keys/tokens) in generated code — generated servers read them from environment variables only.
- All outbound HTTP fetches of user-supplied URLs MUST go through `app/services/url_fetcher.py` (SSRF protections) — no raw `httpx.get`/`requests.get` on user input anywhere else in the codebase.
- No comments explaining *what* code does; only non-obvious *why* comments, sparingly.
- Async I/O (`httpx.AsyncClient`, `async def` routes/services) throughout the request path.

## Already built (do not recreate)

- `app/config.py` — env vars, SSRF blocklists (`BLOCKED_NETWORKS`, `BLOCKED_HOSTNAMES`), thresholds (`REQUEST_TIMEOUT`, `MAX_RESPONSE_SIZE`, `MAX_DISCOVERY_PAGES`, `MAX_REDIRECTS`), paths (`DATA_DIR`, `PROJECTS_DIR`, `GENERATED_DIR`, `DEMO_SPEC_PATH`), `OPENAPI_CANDIDATE_PATHS`.
- `app/models/api.py` — `Parameter`, `RequestBody`, `Response`, `SecurityScheme`, `Endpoint`, `APIRepresentation`, `DiscoveryResult`, plus enums `ParamLocation`, `HttpMethod`, `SpecType`, `AuthType`.
- `app/models/mcp.py` — `MCPParameter`, `MCPTool`, `MCPServerDesign`, `GeneratedFile`, `GeneratedMCPServer`, `ValidationCheck`, `ValidationResult`, `GenerationPreferences`, `MCPProject`.
- `app/models/project.py` — `ProjectMetadata`, `ProjectSummary`, `HistoryResponse`.
- `app/data/demo_openapi.json` — fixture OpenAPI 3.0 spec ("Task Manager API", 8 endpoints, bearer auth) used by Demo Mode and by tests.
- `requirements.txt`, `pyproject.toml`, `.env.example`, directory skeleton (`app/routes/`, `app/services/`, `app/templates/`, `app/static/js`, `app/static/css`, `tests/`, `generated-projects/`).

Read these files before writing any code that touches them.

## Work packages (each is one agent)

### A. Discovery + Parsing + Analysis — `app/services/url_fetcher.py`, `app/services/api_discovery.py`, `app/services/openapi_parser.py`, `app/services/documentation_parser.py`, `app/services/api_analyzer.py`

`url_fetcher.py`:
```python
class SSRFError(Exception): ...

@dataclass
class FetchResult:
    url: str
    status_code: int
    content_type: str
    text: str
    headers: dict[str, str]

def validate_url_format(url: str) -> tuple[bool, str | None]: ...
async def safe_fetch(url: str, *, max_size: int = MAX_RESPONSE_SIZE, timeout: float = REQUEST_TIMEOUT, max_redirects: int = MAX_REDIRECTS) -> FetchResult: ...
```
Requirements (task.md §11): HTTPS preferred but http allowed with a warning; block `BLOCKED_HOSTNAMES`; resolve hostname via `socket.getaddrinfo` and reject if **any** resolved address falls in `BLOCKED_NETWORKS` (DNS-rebinding safe); disable httpx auto-redirects, manually follow up to `max_redirects`, re-validating each hop's host/IP before connecting; stream the body and abort once `max_size` bytes are exceeded; restrict `Content-Type` to `ALLOWED_CONTENT_TYPES`; never execute fetched JS/HTML.

`api_discovery.py`:
```python
async def discover_api(url: str) -> DiscoveryResult: ...
```
Order of attempts: (1) if the URL itself resolves to JSON/YAML that looks like an OpenAPI/Swagger doc, use it directly; (2) try `OPENAPI_CANDIDATE_PATHS` under the URL's origin; (3) fetch the URL as HTML and look for `<link>`/`<a>` references to spec files or doc pages matching `DOC_LINK_KEYWORDS`, following up to `MAX_DISCOVERY_PAGES` total fetches; (4) if nothing machine-readable found but HTML was fetched, return `spec_type=SpecType.HTML_DOCS` with the HTML stashed for `documentation_parser`; (5) if nothing at all, `spec_type=SpecType.NONE, success=False, error_message=<clear reason>`.

`openapi_parser.py`:
```python
def detect_spec_version(raw_spec: dict) -> str: ...  # "openapi3" | "swagger2"
def parse_openapi(raw_spec: dict, source_url: str) -> APIRepresentation: ...
```
Full OpenAPI 3.x and Swagger 2.0 support: servers/basePath, all operations per path, parameters (path/query/header/cookie), `requestBody`/`consumes`+body param, responses, `tags`, `operationId` (synthesize `f"{method}_{path_slug}"` when missing), `deprecated`, security requirements → `SecurityScheme` list via `components.securitySchemes` / swagger `securityDefinitions`. Mark `destructive=True` for DELETE, and for PUT/PATCH when the path has a path parameter. Set `Endpoint.source_ref` to something like `"openapi:{method}:{path}"`.

`documentation_parser.py`:
```python
def parse_html_documentation(html: str, source_url: str) -> APIRepresentation: ...
```
Best-effort regex/BeautifulSoup extraction of `METHOD /path` patterns and nearby description text from rendered docs (e.g. `GET /users`). Every endpoint found gets `source_ref="html_docs:{method}:{path}"`. If nothing recognizable is found, return an `APIRepresentation` with empty `endpoints` — the caller decides that's a discovery failure, this function never fabricates endpoints to fill the gap.

`api_analyzer.py`:
```python
def normalize_api(discovery: DiscoveryResult) -> APIRepresentation: ...
def detect_authentication(raw_spec: dict) -> list[SecurityScheme]: ...
def summarize_for_ai(api: APIRepresentation, max_endpoints: int = 60) -> dict: ...
```
`normalize_api` dispatches on `discovery.spec_type` to the two parsers above, dedupes endpoints by `(method, path)`, and raises `ValueError` if `discovery.success` is `False`. `summarize_for_ai` produces a compact JSON-able dict (endpoint list with method/path/summary/params-by-name-and-type only, truncated schemas, grouped by tag) sized to stay well under a few thousand tokens for large APIs — this is what gets sent to OpenAI, never the raw spec.

**Test with:** `app/data/demo_openapi.json` loaded as `raw_spec`, and a couple of hand-built Swagger 2.0 / malformed / non-API-HTML fixtures inline in your own scratch testing (the `tests/` package is owned by another agent — don't add test files yourself, just verify manually with a throwaway script and delete it before finishing).

---

### B. AI Tool Design — `app/services/openai_service.py`, `app/services/mcp_designer.py`

`openai_service.py`:
```python
class OpenAIServiceError(Exception): ...

async def call_structured(
    system_prompt: str,
    user_prompt: str,
    response_model: type[BaseModel],
    *, retries: int = 2,
) -> BaseModel: ...
```
Single centralized entry point for all OpenAI calls (task.md §43) — nothing else in the codebase imports the `openai` package. Uses `AsyncOpenAI(api_key=config.OPENAI_API_KEY)`, model `config.OPENAI_MODEL`, `response_format={"type": "json_object"}`, parses the JSON, validates with `response_model.model_validate`. On `pydantic.ValidationError`, retry with a corrective follow-up prompt that includes the validation error text, up to `retries` times; raise `OpenAIServiceError` with a clean message (no key/prompt leakage) if still invalid. Never raise raw SDK exceptions past this function.

`mcp_designer.py`:
```python
class _AIToolParam(BaseModel):
    name: str; type: str; description: str; required: bool = False; default: Any | None = None

class _AIToolSpec(BaseModel):
    name: str; description: str; method: str; path: str
    parameters: list[_AIToolParam] = []
    group: str = "general"

class _AIDesignResponse(BaseModel):
    server_name: str; description: str
    tools: list[_AIToolSpec]
    ignored_endpoints: list[str] = []
    reasoning: str = ""

async def design_tools(api: APIRepresentation) -> MCPServerDesign: ...
def build_demo_design() -> tuple[APIRepresentation, MCPServerDesign]: ...
```
`design_tools`: build a system prompt describing the MCP-tool-design task (merge/rename/skip endpoints for a clean developer interface — task.md §14–15), call `openai_service.call_structured(..., response_model=_AIDesignResponse)` with `api_analyzer.summarize_for_ai(api)` as the user payload, then **cross-validate**: for every `_AIToolSpec`, find a matching `Endpoint` in `api.endpoints` by `(method.upper(), path)`; if no match, drop the tool and add it to `ignored_endpoints` instead (never trust the model's method/path verbatim). Copy `destructive` from the matched `Endpoint`. Build `input_schema` (JSON Schema `object` with `properties`/`required`) from the tool's parameters. Return a fully-populated `MCPServerDesign`.

`build_demo_design()`: loads `config.DEMO_SPEC_PATH`, parses it via `openapi_parser.parse_openapi` (import from package A — by the time agents integrate this will exist; if `config.OPENAI_API_KEY` is empty, return a **fixed, hand-written** `MCPServerDesign` for the demo spec instead of calling OpenAI, so Demo Mode works with zero API key (task.md §46). Hand-write all 8 tools (list/get/create/update/delete tasks, list/create projects, delete project) matching the demo spec exactly.

---

### C. Generation + Validation + Storage — `app/services/mcp_generator.py`, `app/services/validator.py`, `app/services/project_store.py`, `app/templates/mcp_project/*.py.jinja`

`mcp_generator.py`:
```python
def generate_server(api: APIRepresentation, design: MCPServerDesign, preferences: GenerationPreferences | None = None) -> GeneratedMCPServer: ...
def render_mcp_client_config(design: MCPServerDesign) -> str: ...
```
Applies `preferences` first: filter `design.tools` by `include_read_only`/`include_destructive`, honor `selected_tool_names` if set, group into modules by `group` when `group_by_resource` (else one `tools/api.py`). Render Jinja2 templates from `app/templates/mcp_project/` (create this directory with `.j2` templates — see structure below) into a flat list of `GeneratedFile`. Output structure (task.md §17):
```
src/server.py       # MCP server init, imports + registers every tool module
src/config.py        # reads API_BASE_URL/API_KEY/API_TOKEN from env via pydantic-settings-style class
src/client.py        # shared async httpx client: base_url, auth header injection, timeout/error handling
src/models.py         # Pydantic models for tool inputs (one per tool, from input_schema)
src/tools/__init__.py
src/tools/<group>.py  # one @tool-decorated function per MCPTool in that group, calls client.py
tests/test_client.py  # generated only if preferences.generate_tests
tests/test_tools.py   # generated only if preferences.generate_tests
.env.example           # API_BASE_URL=, API_KEY=, API_TOKEN= (only the ones design.auth_type needs)
.gitignore
requirements.txt        # mcp, httpx, pydantic, python-dotenv, pinned
README.md                # generated only if preferences.generate_docs; call render_readme (this file, below)
mcp-config.json          # from render_mcp_client_config
pyproject.toml
```
Use the current official `mcp` Python package (`from mcp.server.fastmcp import FastMCP`) for `src/server.py` — tools register with `@mcp.tool()` decorators, one per generated tool function, description = `MCPTool.description`, input validated against the matching `src/models.py` Pydantic model. Every tool function must: build the request via `client.py`, catch `httpx.HTTPStatusError`/`httpx.TimeoutException`/`httpx.RequestError` and return a clean structured error dict (never a raw traceback), and return `response.json()` (or `{"result": response.text}` for non-JSON / empty bodies).

Also add, in this same file:
```python
def render_readme(api: APIRepresentation, design: MCPServerDesign, files: list[GeneratedFile]) -> str: ...
```
Real README content generated from the actual `design.tools` (name/method/path/params per tool), not generic boilerplate — task.md §23.

`validator.py`:
```python
def validate_generated_server(server: GeneratedMCPServer) -> ValidationResult: ...
```
Checks (each becomes a `ValidationCheck`, task.md §21–22): required files present (`src/server.py`, `src/config.py`, `src/client.py`, `requirements.txt`, `.env.example`); every `.py` `GeneratedFile.content` passes `ast.parse` (report the exact `SyntaxError` message on failure); `src/server.py` contains an MCP server instantiation and at least one registered tool; every tool has a JSON-schema-shaped `input_schema` (dict with `"type": "object"`); `.env.example` contains the env vars `config.py` reads; `requirements.txt` is non-empty and includes `mcp`. Missing optional files (e.g. tests when `generate_tests=False`) are not failures. `passed = True` only if zero `severity="error"` checks failed; missing-but-optional or soft issues are `severity="warning"` and don't fail the build (e.g. "OAuth requires manual credentials" when `auth_type == OAUTH2`).

`project_store.py`:
```python
def create_project(source_url: str) -> MCPProject: ...
def save_project(project: MCPProject) -> None: ...
def load_project(project_id: str) -> MCPProject | None: ...
def list_projects(limit: int = 50) -> list[ProjectMetadata]: ...
def delete_project(project_id: str) -> None: ...
def save_generated_files_to_disk(project_id: str, server: GeneratedMCPServer) -> Path: ...
def build_zip(project_id: str) -> Path: ...
```
JSON files at `config.PROJECTS_DIR / f"{project_id}.json"` (one file per project, `MCPProject.model_dump(mode="json")`). `project_id` = `uuid4().hex[:12]`. `save_generated_files_to_disk` writes each `GeneratedFile` under `config.GENERATED_DIR / project_id / <file.path>`, creating parent dirs. `build_zip` zips that directory to `config.GENERATED_DIR / f"{project_id}.zip"` and returns its path (build it fresh each call, not cached — projects are small).

---

### D. Routes + App Entrypoint — `app/main.py`, `app/routes/pages.py`, `app/routes/analysis.py`, `app/routes/generation.py`, `app/routes/projects.py`, `app/routes/downloads.py`

Write against the interfaces documented in packages A/B/C above even though those files may not exist yet when you start — they will by integration time; import paths are fixed (`from app.services.url_fetcher import safe_fetch`, etc.). Every route stores/loads state via `project_store` — nothing is kept in memory between requests.

`app/routes/pages.py` (`APIRouter()`, no prefix, returns `Jinja2Templates` `TemplateResponse`):
```
GET /            -> templates/index.html   (marketing/home page)
GET /builder      -> templates/builder.html  (core app)
GET /history       -> templates/history.html
GET /project/{id}  -> templates/project.html (404 page if project_store.load_project returns None)
```

`app/routes/analysis.py` (`APIRouter(prefix="/api")`):
```
POST /api/discover      {"url": str}                 -> 200 {"project_id": str, "discovery": DiscoveryResult}
                                                          400 {"detail": <human-readable reason>} on invalid URL / SSRF block / no API found
POST /api/analyze       {"project_id": str}           -> 200 {"api": APIRepresentation}
POST /api/design-tools  {"project_id": str, "demo": bool = False} -> 200 {"design": MCPServerDesign}
```
Each endpoint loads the project via `project_store.load_project`, calls the corresponding service, mutates `MCPProject.{api,design}` + `status`, calls `project_store.save_project`, and returns the fresh sub-object. On any service exception, set `project.status="failed"`, `project.error_message=str(e)`, save, and respond `502`/`400` as appropriate with a clear `detail` message — never a bare 500 with a stack trace (task.md §34–35).

`app/routes/generation.py` (`APIRouter(prefix="/api")`):
```
POST /api/generate    {"project_id": str, "preferences": GenerationPreferences | None} -> 200 {"generated": {"server_name": str, "tool_count": int, "files": [str]}, "validation": ValidationResult}
POST /api/validate     {"project_id": str}            -> 200 {"validation": ValidationResult}
POST /api/regenerate   {"project_id": str, "preferences": GenerationPreferences} -> same shape as /generate
```
`/generate` calls `mcp_generator.generate_server`, then `project_store.save_generated_files_to_disk`, then `validator.validate_generated_server`, saves everything onto the `MCPProject`, sets `status="ready"` (or `"failed"` if validation has errors — but still save the files so the user can see what went wrong). `/regenerate` re-runs generation with new preferences against the *existing* `project.api`/`project.design` — no re-discovery needed (task.md §30).

`app/routes/projects.py` (`APIRouter(prefix="/api")`):
```
GET  /api/project/{id}          -> 200 MCPProject | 404
GET  /api/project/{id}/files     -> 200 {"files": [GeneratedFile]}
GET  /api/project/{id}/tools     -> 200 {"tools": [MCPTool]}
GET  /api/history                -> 200 HistoryResponse
DELETE /api/project/{id}          -> 200 {"ok": true}
POST /api/project/{id}/feedback   {"rating": int, "comment": str = ""} -> 200 {"ok": true}  (append to project.preferences or a sibling "feedback" key you add to the stored JSON — don't change the MCPProject model; store via a small dict merge in project_store's JSON file directly)
```

`app/routes/downloads.py` (`APIRouter(prefix="/api")`):
```
GET /api/project/{id}/download          -> FileResponse (zip, from project_store.build_zip), media_type="application/zip"
GET /api/project/{id}/file?path=<rel>    -> 200 {"path": str, "content": str} | 404 (reads one GeneratedFile's content for "copy file")
```

`app/main.py`:
```python
app = FastAPI(title="MCP Server Builder")
```
CORS middleware from `config.CORS_ORIGINS`; mount `app/static` at `/static`; `Jinja2Templates(directory="app/templates")` shared via `app.state.templates` or a small `app/templates_engine.py` — pick one and use it consistently in every router; include all five routers; global exception handler that turns any uncaught exception into `{"detail": "Internal error"}` with `logging.exception(...)` server-side (never leak internals to the client, task.md §21/34); `GET /health -> {"status": "ok"}`; `GET /robots.txt` and `GET /sitemap.xml` serving static files from `app/static/`.

---

### E. Frontend — `app/templates/index.html`, `app/templates/builder.html`, `app/templates/history.html`, `app/templates/project.html`, `app/static/js/app.js`, `app/static/js/builder.js`, `app/static/js/history.js`, `app/static/js/project.js`, `app/static/css/styles.css`, `app/static/robots.txt`, `app/static/sitemap.xml`

Load and follow the **ui-ux-pro-max** skill for this package. Tailwind via the CDN script (`<script src="https://cdn.tailwindcss.com">`) — no build step, per task.md §2. Light theme, restrained developer-SaaS aesthetic — see task.md §5 for the full do/don't list (no gradients-everywhere, no dark-only, no generic AI-purple branding). Use `highlight.js` via CDN for code blocks (project.html / builder.html code viewer).

This package implements task.md §6, §7, §8, §9, §19, §20, §26–29, §31–33 (client-side only — never fabricate results; every button calls the API below and renders the real response), §36–40.

**API contract this package consumes** (all under `/api`, JSON in/out, defined in package D above):
- `POST /discover {url}` → `{project_id, discovery}`
- `POST /analyze {project_id}` → `{api}`
- `POST /design-tools {project_id, demo}` → `{design}` — `design.tools` each carry `selected: bool`; tool-selection UI toggles this client-side, sent back in `/generate`'s `preferences.selected_tool_names`
- `POST /generate {project_id, preferences}` → `{generated, validation}`
- `POST /validate {project_id}` → `{validation}`
- `POST /regenerate {project_id, preferences}` → `{generated, validation}`
- `GET /project/{id}` → full `MCPProject`
- `GET /project/{id}/files` → `{files}`
- `GET /project/{id}/tools` → `{tools}`
- `GET /history` → `{projects, total}`
- `GET /project/{id}/download` → zip (trigger `window.location`)
- `GET /project/{id}/file?path=` → `{content}` (for "copy file")
- `DELETE /project/{id}`
- `POST /project/{id}/feedback {rating, comment}`

**Builder pipeline (`builder.js`)** drives the stage tracker (task.md §9) by making the calls above *sequentially*, updating a visible stage (`waiting → running → done/failed`) around each real network call — never a fake `setTimeout` progress bar. Stages: Connecting → Inspecting documentation → Detecting API spec → Parsing endpoints → Understanding authentication → Designing MCP tools → (tool review pause — user reviews/deselects tools, then clicks Generate) → Generating server → Validating implementation → Ready.

Recent URLs (task.md §8) and Demo Mode entry point live in `localStorage` (`mcp-builder:recent-urls`). Demo Mode (`app.js`/`builder.js`) posts `{"url": "demo://task-manager", "demo": true}`-shaped requests, or simpler: a "Try the demo" button that calls `/api/discover` with the real demo spec's public identifier — coordinate the exact request shape with package D's `/discover`/`design-tools` (`demo` flag) if you finish first; otherwise match what D implements (read `app/routes/analysis.py` once it exists).

---

### F. Tests — `tests/test_security.py`, `tests/test_discovery.py`, `tests/test_designer.py`, `tests/test_generation.py`, `tests/test_validation.py`, `tests/conftest.py`

Use `pytest`, `pytest-asyncio` (already `asyncio_mode = "auto"` in `pyproject.toml`), and `respx` to intercept `httpx` calls — never hit the real network. Fixtures in `conftest.py`: a `tmp_path`-scoped override of `config.DATA_DIR`/`PROJECTS_DIR`/`GENERATED_DIR` (monkeypatch) so tests don't write into the real `app/data`, and a loaded copy of `app/data/demo_openapi.json`.

- `test_security.py`: `url_fetcher.validate_url_format` and `safe_fetch` — localhost blocked, `127.0.0.1`/`10.x`/`192.168.x`/`169.254.x` blocked, a DNS name mocked (via monkeypatching `socket.getaddrinfo`) to resolve to a private IP is blocked (rebinding case), invalid URL strings rejected, a redirect chain (respx) to a blocked IP is rejected, oversized response (respx streaming a body over `MAX_RESPONSE_SIZE`) raises.
- `test_discovery.py`: `discover_api` finds an OpenAPI doc at `/openapi.json` (respx-mocked), finds Swagger 2.0, falls back to HTML docs parsing, returns `success=False` with a clear message for a plain non-API site. `openapi_parser.parse_openapi` against `app/data/demo_openapi.json` produces exactly 8 endpoints with correct methods/paths/`destructive` flags.
- `test_designer.py`: mock `openai_service.call_structured` (monkeypatch, don't hit OpenAI) to return a valid `_AIDesignResponse` and confirm `design_tools` cross-validates and drops a tool whose path doesn't exist in `api.endpoints`; also a malformed/missing-field case that should raise `OpenAIServiceError` after exhausting retries; `build_demo_design()` works with `OPENAI_API_KEY` unset.
- `test_generation.py`: `generate_server` on the demo API+design produces all required files, `ast.parse` succeeds on every `.py` file, `preferences.include_destructive=False` excludes `delete_task`/`delete_project`.
- `test_validation.py`: a good `GeneratedMCPServer` passes; inject a syntax error into one file's content and confirm `validate_generated_server` reports it with the exact file and a `severity="error"` check, `passed=False`.

Run `pytest` from repo root when done; all tests in your files must pass against the interfaces above (mock anything from other packages that isn't ready yet, but don't rewrite their signatures).

---

### G. Documentation — `README.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/DEPLOYMENT.md`, `docs/TESTING.md`, `docs/CONTRIBUTING.md`, `CHANGELOG.md`

Read the existing root `README.md`, `AGENT.md`, `CLAUDE.md`, and `LICENSE` first — `CLAUDE.md` at the repo root is the maintained developer-instructions doc and should stay (only touch it if something it documents has clearly changed shape, e.g. exact file paths under `app/`); leave it as the authoritative dev doc, don't duplicate its content elsewhere. `LICENSE` already exists — read it, don't overwrite unless it's empty or wrong (report if so instead of guessing the license type).

- **`AGENTS.md`** (new, repo root): rewrite `AGENT.md`'s content into the now-standard `AGENTS.md` filename/convention — instructions for AI coding agents working in this repo: architecture at a glance, the exact `app/` layout from this contract, how to run (`uvicorn app.main:app --reload --port 8000`), how to test (`pytest`), where the SSRF rules live, where the OpenAI call is centralized, and the "every MCP tool must trace to a real endpoint" anti-hallucination rule. Delete the old `AGENT.md` once `AGENTS.md` is written (git mv semantics — just create the new file and remove the old one).
- **`README.md`** (root, rewrite in place): what the product does, architecture diagram (ASCII, matching this contract's actual `app/` layout), install/run steps matching `requirements.txt`/`.env.example` exactly, the full pipeline (`URL → discover → analyze → design-tools → generate → validate → download`), the route table from package D, security model summary, testing instructions, limitations (e.g. HTML-docs parsing is best-effort, OAuth2 flows need manual credential entry).
- **`docs/ARCHITECTURE.md`**: expand on the diagram — each service's responsibility (one paragraph each, matching packages A/B/C/D above), the `MCPProject` JSON storage model, request/response flow for one full generation.
- **`docs/SECURITY.md`**: the full SSRF threat model from `task.md` §11 mapped to the actual `url_fetcher.py` implementation (once package A lands — read it before writing this), plus "what we protect against" / "what we don't" from `CLAUDE.md`.
- **`docs/DEPLOYMENT.md`**: dev (`uvicorn --reload`) vs prod (`gunicorn` + `UvicornWorker`) commands, required env vars, a note that `app/data/` and `generated-projects/` need a writable volume in production.
- **`docs/TESTING.md`**: how to run the suite from package F, what each test file covers, how to add a new discovery-format test.
- **`docs/CONTRIBUTING.md`**: short — branch naming, running `pytest`/`black`/`isort`/`mypy` before a PR, no secrets in commits.
- **`CHANGELOG.md`**: single `## [0.1.0]` entry summarizing this build (Keep a Changelog format).

Do not invent API routes, file paths, or environment variables that don't exist elsewhere in this contract — cross-check against packages A–F, reading their files once available rather than guessing.

---

## Self-review checklist (each agent, before finishing)

1. Every function signature you implemented matches this contract exactly (name, params, return type).
2. You touched only your assigned files.
3. No secrets, no fabricated endpoints/params, no raw stack traces to clients.
4. `python -m py_compile` (or `ast.parse`) clean on every `.py` file you wrote.
