# Testing

## Running the suite

```bash
pytest                        # run everything
pytest --cov=app               # with coverage
pytest tests/test_security.py -v
pytest tests/test_discovery.py::test_openapi_parsing -vvs   # single test, verbose, no capture
```

`pytest-asyncio` runs in `asyncio_mode = "auto"` (`pyproject.toml`), so `async def test_...`
functions work without extra decorators. All outbound HTTP is intercepted with `respx` — tests
never hit the real network, and OpenAI calls are mocked at the `openai_service.call_structured`
boundary rather than hitting the real API.

`tests/conftest.py` provides:

- a `tmp_path`-scoped monkeypatch of `config.DATA_DIR` / `config.PROJECTS_DIR` /
  `config.GENERATED_DIR`, so no test writes into the real `app/data` or `generated-projects`;
- a loaded copy of `app/data/demo_openapi.json` as a fixture for discovery/design/generation
  tests.

## What each test file covers

### `tests/test_security.py`

SSRF protection in `app/services/url_fetcher.py`:

- `validate_url_format` rejects malformed URLs, non-http(s) schemes, and blocked hostnames.
- `safe_fetch` blocks direct requests to `127.0.0.1`, `10.x`, `192.168.x`, `169.254.x`, etc.
- a DNS name mocked (via monkeypatching `socket.getaddrinfo`) to resolve to a private IP is
  blocked — the DNS-rebinding case.
- a `respx`-mocked redirect chain that ends at a blocked IP is rejected, not silently followed.
- a `respx`-mocked oversized response (streaming past `MAX_RESPONSE_SIZE`) raises `SSRFError`.

### `tests/test_discovery.py`

- `discover_api` finds an OpenAPI doc served at `/openapi.json` (respx-mocked), finds a Swagger
  2.0 doc, falls back to HTML docs parsing when no machine-readable spec is found, and returns
  `success=False` with a clear `error_message` for a plain non-API site.
- `openapi_parser.parse_openapi` run against `app/data/demo_openapi.json` produces exactly 8
  endpoints with the correct methods, paths, and `destructive` flags.

### `tests/test_designer.py`

- `openai_service.call_structured` is monkeypatched (never hits real OpenAI) to return a valid
  `_AIDesignResponse`; confirms `design_tools` cross-validates and drops any tool whose
  `(method, path)` doesn't match a real `Endpoint`, moving it into `ignored_endpoints`.
- a malformed/missing-field mocked response results in `OpenAIServiceError` after retries are
  exhausted.
- `build_demo_design()` produces a working design with `OPENAI_API_KEY` unset (Demo Mode path).

### `tests/test_generation.py`

- `generate_server` run against the demo API + design produces every required file.
- `ast.parse` succeeds on every generated `.py` file.
- `preferences.include_destructive=False` excludes destructive tools (e.g. `delete_task`,
  `delete_project`) from the generated output.

### `tests/test_validation.py`

- A well-formed `GeneratedMCPServer` passes validation cleanly.
- A syntax error injected into one file's content is reported by
  `validate_generated_server` against the exact file, as a `severity="error"` check, with
  `passed=False` overall.

## Adding a new discovery-format test

When adding support for a new documentation/spec format (see the "Add Support for New API
Format" workflow in `CLAUDE.md`):

1. Add a fixture — either a small dict/string built inline in the test, or a new file under a
   `tests/fixtures/` directory if it's large enough to be unwieldy inline.
2. Mock the fetch with `respx` so `discover_api`/`safe_fetch` see your fixture content instead of
   a real network call — mock at the URL level (e.g. `respx.get("https://example.com/openapi.json").mock(...)`).
3. Assert on the `DiscoveryResult` (`spec_type`, `success`, `raw_spec`/discovered pages) and, if
   your format has its own parser, on the resulting `APIRepresentation` (endpoint count, methods,
   paths — mirror the assertions in the existing `test_openapi_parsing`-style test).
4. If nothing recognizable should be found, assert `success is False` with a clear
   `error_message` rather than an empty-but-successful result — discovery failures must be
   explicit, never silently mistaken for "zero endpoints found."
5. Run `pytest tests/test_discovery.py -v` to confirm the new case passes alongside the existing
   ones.
