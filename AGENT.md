# AGENT.md – AI Agent Instructions

This document is for AI agents (Claude, other LLMs) working on the MCP Server Builder codebase.

## Project Overview

**MCP Server Builder** automatically generates production-ready MCP (Model Context Protocol) servers from API documentation URLs. The pipeline is:

```
User Input (URL)
    ↓
Validation (SSRF protection)
    ↓
Discovery (Parse API docs/OpenAPI/Swagger)
    ↓
Analysis (Extract endpoints, params, auth)
    ↓
AI Design (GPT-4 creates tool schema)
    ↓
Generation (Jinja2 renders MCP server code)
    ↓
Validation (Check syntax and MCP compliance)
    ↓
Storage & Delivery (Save project, return ZIP)
```

## Architecture Overview

### Components & Responsibilities

| Component | Technology | Responsibility |
|-----------|-----------|-----------------|
| **Web UI** | HTML5 + Tailwind + Vanilla JS | URL input, progress tracking, results display |
| **FastAPI Backend** | Python 3.8+ | Request routing, validation, orchestration |
| **Discovery Service** | httpx, BeautifulSoup (optional) | Fetch and identify API documentation format |
| **Analysis Service** | Built-in parsing | Extract endpoints, parameters, responses from specs |
| **Designer Service** | OpenAI API | AI-driven MCP tool design from API analysis |
| **Generator Service** | Jinja2 | Render Python code from tool design |
| **Validator Service** | AST, imports | Validate generated code syntax and completeness |
| **Project Storage** | JSON files in `app/data/` | Persist projects for history/download |

### Data Flow Diagram

```
Frontend Form
    ↓ POST /api/discover
[URL Validation]
    ├─ IP check (SSRF protection)
    ├─ Format check (https://)
    └─ Redirect validation (max 5 hops)
    ↓
[Discovery] 
    ├─ Fetch URL content
    ├─ Detect format (OpenAPI/Swagger/HTML)
    ├─ Find spec file (openapi.json, swagger.yaml)
    └─ Parse documentation
    ↓ DiscoveryResult
[Analysis]
    ├─ Normalize endpoints
    ├─ Extract parameters (path, query, body)
    ├─ Extract responses
    ├─ Identify auth (API key, OAuth, Bearer)
    └─ Detect patterns (CRUD, etc.)
    ↓ APIRepresentation
[Design] (AI)
    ├─ Build GPT-4 prompt with API analysis
    ├─ Call OpenAI API
    ├─ Parse tool definitions from response
    └─ Create MCPServerDesign
    ↓ MCPServerDesign
[Generation]
    ├─ Render templates (main.py, tools.py, config.py)
    ├─ Include dependencies (requirements.txt)
    ├─ Add documentation (README.md)
    └─ Package project structure
    ↓ GeneratedMCPServer
[Validation]
    ├─ Check Python syntax
    ├─ Verify imports exist
    ├─ Check MCP schema compliance
    └─ Test basic tool instantiation
    ↓
[Storage]
    ├─ Save project metadata to JSON
    ├─ Store generated files
    └─ Create downloadable ZIP
    ↓
Return to frontend (project_id, files, download_link)
```

## API Contracts & Data Models

### Input Models (Pydantic)

**URL Discovery Request**
```python
class DiscoverRequest(BaseModel):
    url: str  # https://...
    follow_links: bool = True  # Discover linked docs
    timeout: int = 20  # Seconds
```

**Response Format** (all endpoints)
```python
class APIResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any]  # timestamp, version, etc.
```

### Core Data Models

**Endpoint** (from `app/models/api.py`)
```python
class Endpoint(BaseModel):
    path: str              # "/users/{id}"
    method: str            # "GET", "POST", etc.
    summary: Optional[str]
    description: Optional[str]
    operation_id: Optional[str]
    tags: List[str]        # ["users", "accounts"]
    parameters: List[Parameter]
    request_body: Optional[RequestBody]
    responses: List[Response]
    security: Optional[List[Dict[str, List[str]]]]
```

**APIRepresentation** (discovered API)
```python
class APIRepresentation(BaseModel):
    name: str                                # "GitHub API"
    description: Optional[str]
    version: Optional[str]                  # "2024-01-01"
    base_url: Optional[str]                 # "https://api.github.com"
    source_url: str                         # URL we discovered it from
    endpoints: List[Endpoint]               # All discovered endpoints
    security_schemes: Dict[str, SecurityScheme]
    tags: Dict[str, str]                    # tag descriptions
    authentication_required: bool
    authentication_type: Optional[str]      # "api_key", "oauth2", "bearer"
```

**MCPTool** (single MCP tool definition)
```python
class MCPTool(BaseModel):
    name: str                               # "get_user"
    description: str                        # What the tool does
    category: Optional[str]                 # "data_retrieval", "data_modification"
    api_endpoint: str                       # "GET /users/{id}"
    method: str                             # "GET"
    path: str                               # "/users/{id}"
    parameters: List[ToolParameter]         # Input schema
    input_schema: ToolInputSchema           # JSON Schema
    required_auth: Optional[str]            # Auth method
    rate_limit_info: Optional[str]
    example_request: Optional[Dict]         # Sample request
    example_response: Optional[Dict]        # Sample response
```

**MCPServerDesign** (complete design)
```python
class MCPServerDesign(BaseModel):
    server_name: str                        # "github-mcp"
    server_description: str
    version: str = "0.1.0"
    tools: List[MCPTool]                    # All designed tools
    authentication_config: Optional[Dict]   # How to auth to API
    api_base_url: str
    source_api_name: str
```

## Common Patterns Used

### 1. Service Pattern
Each major operation is a service with clean interface:

```python
# app/services/discovery.py
async def discover_api(url: str) -> DiscoveryResult:
    """Discover API documentation at URL."""
    # Validate URL
    # Fetch content
    # Detect format
    # Parse spec
    # Return DiscoveryResult
```

### 2. Pydantic Validation
All inputs/outputs use Pydantic models for validation:

```python
# FastAPI automatically validates and converts
@app.post("/api/discover")
async def discover_endpoint(request: DiscoverRequest) -> APIResponse:
    # request.url is guaranteed valid string
    # request.follow_links is guaranteed bool
```

### 3. Error Handling Pattern
```python
class AppException(Exception):
    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code

# In routes
try:
    result = await discover_api(url)
except AppException as e:
    return {"success": False, "error": e.message}
```

### 4. Async/Await
All I/O operations are async:

```python
async def discover_api(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=20)
        # ...
```

## What NOT to Do

### ❌ Don't
- **Hardcode API keys** – Use environment variables only
- **Trust user input** – Always validate/sanitize
- **Make blocking calls** – Use async/await for all I/O
- **Ignore SSRF risks** – Check IP ranges in config.py before HTTP requests
- **Log sensitive data** – Never log API keys, auth tokens, or user data
- **Modify core models** – Extend them properly, don't break contract
- **Skip validation** – Use Pydantic models for all external input
- **Generate untested code** – Run syntax validation on generated files
- **Return detailed errors** – Don't expose internal paths/stack traces to client
- **Commit .env files** – Use .env.example only

### ⚠️ Be Careful With
- **OpenAI API calls** – They cost money and have rate limits
- **Large API responses** – Enforce MAX_RESPONSE_SIZE (10MB)
- **Recursive link following** – Cap at MAX_DISCOVERY_PAGES (10)
- **Generated code** – It runs on user machines; ensure it's safe
- **Project storage** – Disk space grows; implement cleanup policy

## How to Add New Features

### Example: Add Support for Postman Collections

1. **Update Models** (`app/models/api.py`)
   ```python
   class PostmanCollection(BaseModel):
       name: str
       description: Optional[str]
       item: List[Dict[str, Any]]  # Requests
   
   # Extend APIRepresentation or map to it
   ```

2. **Update Discovery** (`app/services/discovery.py`)
   ```python
   async def discover_api(url: str):
       content = await fetch_url(url)
       
       # Detect Postman collection
       if is_postman_collection(content):
           collection = parse_postman(content)
           # Convert to APIRepresentation
           return DiscoveryResult(
               api=postman_to_api(collection),
               detected_type="postman"
           )
   ```

3. **Add Tests**
   ```python
   # tests/test_discovery.py
   async def test_discover_postman_collection():
       result = await discover_api("https://...")
       assert result.detected_type == "postman"
       assert len(result.api.endpoints) > 0
   ```

4. **Update Documentation** (`API_REFERENCE.md`, `ARCHITECTURE.md`)

## How to Debug Issues

### Issue: Generated MCP server won't import

1. **Check syntax**
   ```bash
   python -m py_compile app/data/{project_id}/main.py
   ```

2. **Check imports**
   ```bash
   python -c "import sys; sys.path.insert(0, 'app/data/{project_id}'); import main"
   ```

3. **Check dependencies**
   ```bash
   pip install --dry-run -r app/data/{project_id}/requirements.txt
   ```

4. **Review generated code**
   - Check `app/data/{project_id}/main.py`
   - Look for typos or undefined variables
   - Verify all imports are available

### Issue: SSRF Protection False Negatives

Test:
```python
from app.services.security import is_safe_url

# Should reject
assert not is_safe_url("http://127.0.0.1:9000")
assert not is_safe_url("http://192.168.1.1")
assert not is_safe_url("http://localhost")

# Should allow
assert is_safe_url("https://api.github.com")
assert is_safe_url("https://example.com")
```

If failing, check:
1. Config IP blocklist in `app/config.py`
2. Hostname resolution (DNS lookup)
3. Redirect handling (follow_redirects check)

### Issue: Generated Server Doesn't Match API

1. **Review discovery result**
   - Check if endpoints were found: `len(result.api.endpoints)`
   - Check if auth was detected: `result.api.authentication_required`

2. **Review design result**
   - Check tool count: `len(design.tools)`
   - Check tool descriptions make sense
   - Review tool parameters match endpoints

3. **Review generation result**
   - Check `generated_server.errors`
   - Check `generated_server.warnings`
   - Review generated tool implementations

## Testing Expectations

### Unit Tests
- Mock external APIs (OpenAI, HTTP)
- Test each service independently
- Cover happy path + error cases
- Target 80%+ line coverage

### Integration Tests
- Use real fixture APIs (e.g., httpbin for testing HTTP)
- Test full pipeline end-to-end
- Verify generated code runs without errors

### Security Tests
- SSRF: Test blocked IPs, domains, redirects
- Validation: Test invalid URLs, oversized responses
- Auth: Verify keys never logged or exposed

### Manual Testing
- Test with real APIs (GitHub, Stripe, Twilio, etc.)
- Run generated servers and verify they work
- Test on different OS (Windows/Mac/Linux)

## File Organization & Naming

```
app/
├── __init__.py
├── config.py                  # Configuration, constants
├── main.py                    # FastAPI app, routes
├── models/
│   ├── __init__.py
│   ├── api.py                # API representation
│   ├── mcp.py                # MCP server design
│   └── project.py            # Project metadata
├── services/
│   ├── __init__.py
│   ├── discovery.py          # API discovery
│   ├── analyzer.py           # API analysis
│   ├── designer.py           # MCP tool design (AI)
│   ├── generator.py          # Code generation
│   ├── validator.py          # Validation
│   └── storage.py            # Project persistence
├── utils/
│   ├── __init__.py
│   ├── http.py               # HTTP client with SSRF protection
│   ├── validation.py         # URL/input validation
│   └── errors.py             # Exception classes
└── data/                      # Generated projects (project_id.json)

templates/
├── mcp_main.py.jinja2         # Main MCP server template
├── mcp_tools.py.jinja2        # Tools implementation template
├── mcp_config.py.jinja2       # Configuration template
└── mcp_readme.md.jinja2       # Generated README template

tests/
├── __init__.py
├── test_security.py           # SSRF, URL validation
├── test_discovery.py          # Discovery service
├── test_analyzer.py           # Analysis service
├── test_designer.py           # Design service
├── test_generator.py          # Generation service
└── fixtures/                  # Sample APIs, responses
```

### Naming Conventions
- **Services**: Verb-based (`discovery.py`, `analyzer.py`)
- **Functions**: Snake case (`discover_api()`, `parse_openapi()`)
- **Classes**: Pascal case (`DiscoveryResult`, `MCPTool`)
- **Variables**: Snake case (`project_id`, `source_url`)
- **Constants**: Upper case (`MAX_RESPONSE_SIZE`, `OPENAI_MODEL`)

## How to Submit Changes

### Before Committing
1. Run tests: `pytest --cov=app`
2. Format code: `black app/ tests/`
3. Check types: `mypy app/`
4. Lint: `flake8 app/`

### Commit Message Format
```
[service] Brief description (50 char)

Longer explanation if needed (72 char wrap).

- Bullet point 1
- Bullet point 2

Fixes: #123
```

Examples:
```
[discovery] Add support for RAML API specifications

Extends discovery service to detect and parse RAML 1.0
definitions. Includes link following for included files.

Fixes: #45
```

### PR Checklist
- [ ] Tests pass (`pytest`)
- [ ] Code formatted (`black`)
- [ ] Types checked (`mypy`)
- [ ] New tests added for new logic
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated

## Key Metrics & Instrumentation

### What to Log
```python
import logging
logger = logging.getLogger(__name__)

# Log key events
logger.info(f"Discovering API at: {url}")
logger.debug(f"Found {len(endpoints)} endpoints")
logger.warning(f"Max discovery pages reached: {url}")
logger.error(f"Generation failed: {error}")
```

### Metrics to Track
- Discovery success rate
- Average tool design time
- Generated code validation errors
- User satisfaction (feedback on generated servers)

## Fast Troubleshooting Guide

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "OPENAI_API_KEY not found" | Missing .env | `cp .env.example .env && edit` |
| Port already in use | Another process on :8000 | `uvicorn ... --port 8001` |
| CORS errors in browser | Frontend origin not allowed | Check `CORS_ORIGINS` in config |
| Generated server won't import | Syntax error or bad import | Run `python -m py_compile` |
| AI design is weird | Bad prompt or API structure | Review API analysis, retry design |
| Generated code has typos | Template bug or API inconsistency | Check tool definitions, fix template |
| SSRF protection blocking legit URL | False positive IP check | Check hostname resolution, blocklist |

## Resources & References

- **Model Documentation**: See `app/models/` docstrings
- **Service Code**: See `app/services/` for implementation patterns
- **Tests**: See `tests/` for usage examples
- **Configuration**: See `app/config.py` for security settings
- **Main App**: See `app/main.py` for route definitions

---

**Last Updated**: 2024-01-01  
**For**: AI Agents working on MCP Server Builder
