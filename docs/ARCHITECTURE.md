# Architecture – MCP Server Builder Technical Design

This document describes the technical architecture, system design, data flows, and key decisions in MCP Server Builder.

## System Design Overview

MCP Server Builder is a **stateless, request-driven system** that transforms API documentation URLs into complete MCP server packages.

### Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│                  Frontend Layer                     │
│      HTML5 + Tailwind CSS + Vanilla JavaScript     │
│  (URL input, progress tracking, file browser)      │
└────────────────────┬────────────────────────────────┘
                     │ HTTPS JSON API
┌────────────────────v────────────────────────────────┐
│                 API Layer (FastAPI)                 │
│    Request validation, routing, orchestration      │
│              (8 core endpoints)                     │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────v────────────────────────────────┐
│              Service Layer (Python)                 │
│  ├─ Discovery (fetch, detect, parse API docs)     │
│  ├─ Analyzer (extract endpoints, parameters)       │
│  ├─ Designer (AI-driven tool design via GPT-4)    │
│  ├─ Generator (Jinja2 code rendering)             │
│  └─ Validator (syntax & schema checks)            │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────v────────────────────────────────┐
│            External Dependencies                    │
│  ├─ OpenAI API (GPT-4 for tool design)            │
│  ├─ HTTP Client (httpx + SSRF protection)         │
│  ├─ Jinja2 Templates (code generation)            │
│  └─ JSON File Storage (project persistence)       │
└─────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. Frontend (HTML/CSS/JS)
**Location**: `/index.html`, `/static/client.js`, `/static/styles.css`

**Responsibilities**:
- Display landing page and builder UI
- Accept URL input from users
- Show real-time progress/status
- Display generated project files
- Enable project download
- Responsive design (mobile-first)

**Key Features**:
- Single-page application (no page reloads)
- WebSocket-ready for future real-time updates
- Syntax highlighting for generated code
- Dark mode support

### 2. API Layer (FastAPI)
**Location**: `/app/main.py`

**Responsibilities**:
- Validate incoming requests (Pydantic)
- Route to appropriate services
- Orchestrate multi-step workflows
- Handle errors and return consistent responses
- Serve static files (HTML, CSS, JS)
- CORS configuration

**Key Endpoints**:
```
POST   /api/discover    – API discovery
POST   /api/analyze     – API analysis
POST   /api/design      – Tool design (AI)
POST   /api/generate    – Code generation
POST   /api/validate    – Validation
GET    /api/projects    – List projects
GET    /api/projects/{id} – Get project details
GET    /api/projects/{id}/download – Download ZIP
```

### 3. Discovery Service
**Location**: `/app/services/discovery.py`

**Input**: `url: str` (user-provided URL)

**Output**: `DiscoveryResult` with:
- `api: APIRepresentation` – Normalized API structure
- `raw_spec: Dict` – Original OpenAPI/Swagger spec
- `detected_type: str` – Format (openapi3, swagger2, html_docs, etc.)
- `errors: List[str]` – Any parsing errors
- `warnings: List[str]` – Partial parse warnings

**Responsibilities**:
1. Validate URL (format, SSRF check)
2. Fetch URL content (with timeout, max size limits)
3. Detect documentation format:
   - OpenAPI 3.0 (JSON/YAML)
   - Swagger 2.0
   - HTML documentation
   - Postman collections (future)
4. Find OpenAPI/Swagger specs in common locations
5. Follow documentation links (max 10 pages)
6. Parse and normalize endpoints

**Security Checks**:
- Block private IP ranges (127.x, 10.x, 192.168.x, 172.16-31.x, 224-255.x)
- Validate hostname resolution against blocklist
- Limit redirects to 5 hops
- Enforce 10MB max response size
- Timeout after 20 seconds

### 4. Analyzer Service
**Location**: `/app/services/analyzer.py`

**Input**: `DiscoveryResult` from Discovery

**Output**: Enhanced `APIRepresentation` with:
- Normalized endpoint paths
- Extracted parameters (path, query, body)
- Response schemas
- Security requirements
- API tags and descriptions

**Responsibilities**:
- Extract endpoints from OpenAPI/Swagger specs
- Normalize HTTP methods (GET, POST, etc.)
- Parse parameter definitions
- Extract request/response schemas
- Identify authentication methods (API key, OAuth2, Bearer, etc.)
- Group endpoints by tags
- Detect CRUD patterns
- Extract descriptions and examples

### 5. Designer Service (AI)
**Location**: `/app/services/designer.py`

**Input**: `APIRepresentation` from Analyzer

**Output**: `MCPServerDesign` with:
- Server name and description
- List of `MCPTool` definitions
- Authentication configuration
- Example tool implementations

**Responsibilities**:
1. Build structured prompt from API analysis
2. Call OpenAI GPT-4 with prompt
3. Parse tool definitions from response
4. Validate tool schemas
5. Generate example configurations
6. Ensure logical tool grouping
7. Handle design errors and retries

**Key Prompt Template**:
```
Analyze this API and design MCP tools:

API Name: {api.name}
Base URL: {api.base_url}
Description: {api.description}

Endpoints:
{formatted_endpoints}

Your task:
1. Group related endpoints into logical tools
2. Name tools with clear, descriptive names
3. Design parameters matching API requirements
4. Add helpful descriptions
5. Consider user experience

Return valid JSON with array of tool objects.
```

### 6. Generator Service
**Location**: `/app/services/generator.py`

**Input**: `MCPServerDesign` from Designer

**Output**: `GeneratedMCPServer` with:
- `main_file: str` – Complete main.py
- `tools_file: str` – tools.py with all tool implementations
- `config_file: str` – Configuration template
- `requirements_file: str` – requirements.txt
- `readme_file: str` – README.md
- `errors: List[str]` – Generation errors

**Responsibilities**:
1. Load Jinja2 templates from `/templates/`
2. Render templates with tool definitions
3. Generate main.py (MCP server entry point)
4. Generate tools.py (tool implementations)
5. Generate config.py (authentication setup)
6. Create requirements.txt (dependencies)
7. Generate README.md (usage instructions)
8. Validate generated Python syntax
9. Check template completeness

**Templates Used**:
- `mcp_main.py.jinja2` – Server initialization and tool registration
- `mcp_tools.py.jinja2` – Individual tool implementations
- `mcp_config.py.jinja2` – Configuration and authentication
- `mcp_readme.md.jinja2` – Generated README

### 7. Validator Service
**Location**: `/app/services/validator.py`

**Input**: `GeneratedMCPServer` from Generator

**Output**: `ValidationResult` with:
- `valid: bool` – Whether code is valid
- `errors: List[str]` – Critical issues
- `warnings: List[str]` – Non-critical issues
- `summary: str` – Overall assessment

**Responsibilities**:
1. Check Python syntax (compile)
2. Verify all imports are available
3. Validate MCP schema compliance
4. Test basic tool instantiation
5. Check for missing dependencies
6. Report any issues

**Checks**:
```python
# Syntax validation
compile(code, 'main.py', 'exec')

# Import validation
import ast
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        # Check module available

# Schema validation
jsonschema.validate(tool_schema, MCP_SCHEMA)

# Tool instantiation
tool = MCPTool.model_validate(tool_dict)
```

### 8. Storage Service
**Location**: `/app/services/storage.py`

**Responsibilities**:
- Save project metadata to JSON
- Store generated files
- Retrieve project by ID
- List all projects
- Create downloadable ZIP archive
- Clean up old projects (optional)

**Storage Format**:
```
app/data/
├── {project_id}.json          # Project metadata
└── {project_id}/              # Project files
    ├── main.py
    ├── tools.py
    ├── config.py
    ├── requirements.txt
    └── README.md
```

## Data Flow Diagram

### Complete Pipeline: URL → MCP Server

```
User enters URL
    ↓
HTTP POST /api/discover
    ↓
[URL Validation]
├─ Check format (https://)
├─ Check IP (SSRF protection)
└─ Validate length
    ↓
[Discovery Service]
├─ Fetch URL (with timeout, max size)
├─ Detect format (OpenAPI/Swagger/HTML)
├─ Parse specification
└─ Find linked documentation
    ↓ DiscoveryResult
[Analyzer Service]
├─ Extract all endpoints
├─ Normalize parameters
├─ Identify authentication
└─ Extract descriptions
    ↓ APIRepresentation
[Designer Service]
├─ Build GPT-4 prompt
├─ Call OpenAI API
├─ Parse tool definitions
└─ Validate tool schemas
    ↓ MCPServerDesign
[Generator Service]
├─ Load Jinja2 templates
├─ Render with tool definitions
├─ Validate Python syntax
└─ Package all files
    ↓ GeneratedMCPServer
[Validator Service]
├─ Check syntax
├─ Verify imports
├─ Validate MCP schema
└─ Test instantiation
    ↓ ValidationResult
[Storage Service]
├─ Save metadata to JSON
├─ Store generated files
├─ Create ZIP archive
└─ Return download link
    ↓
Return to frontend (success + download URL)
    ↓
User downloads ZIP
    ↓
User extracts and runs: pip install -r requirements.txt && mcp install
```

## Security Architecture

### SSRF (Server-Side Request Forgery) Protection

**Threat**: Attacker provides URL pointing to internal service (e.g., `http://127.0.0.1:9000`)

**Mitigation Layers**:

1. **IP Blocklist** (primary)
   ```python
   BLOCKED_IP_PATTERNS = [
       "127.",           # Localhost
       "10.",            # Private Class A
       "172.16.",        # Private Class B
       "192.168.",       # Private Class C
       "169.254.",       # Link-local
       "224-255.",       # Multicast/Broadcast
       "::1",            # IPv6 loopback
   ]
   ```

2. **Hostname Resolution Check**
   - Resolve hostname to IP
   - Check resolved IP against blocklist
   - Fail if any blocklist match

3. **Redirect Validation**
   - Follow redirects (max 5 hops)
   - Validate each redirect URL
   - Check destination IP

4. **Request Limits**
   - Max 10MB response body
   - 20-second timeout
   - Max 10 discovery pages

### API Key Security

**Protection**:
- Keys stored in `.env` file (not in code)
- `.env` never committed to git (in `.gitignore`)
- Keys loaded at startup via `python-dotenv`
- Generated servers receive keys via environment
- No logging of sensitive data (implemented via filter)
- Rate limiting ready (tokens tracked per key)

### Code Injection Protection

**Prevention**:
- Validate all API responses before templating
- Sanitize endpoint paths (no special characters)
- Escape parameter values in Jinja2 templates
- Run validators on generated code before returning
- No eval() or exec() on user input

### HTTPS Enforcement

**In Production**:
- Require `https://` scheme (not `http://`)
- Reject insecure URLs
- HSTS headers in responses
- Validate SSL certificates

## API Contract

### Request/Response Envelope

**All responses use consistent format**:

```json
{
  "success": true|false,
  "data": { /* endpoint-specific */ },
  "error": null|"error message",
  "metadata": {
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "0.1.0",
    "request_id": "abc123"
  }
}
```

### Endpoint Specifications

See `API_REFERENCE.md` for complete endpoint documentation.

## Database & Storage

### Data Model (No SQL Database)

**Project Storage** (JSON-based):
```json
{
  "project_id": "proj_abc123",
  "name": "GitHub MCP",
  "description": "MCP server for GitHub API",
  "source_url": "https://api.github.com",
  "source_api_name": "GitHub",
  "created_at": "2024-01-01T12:00:00Z",
  "status": "completed",
  "tool_count": 15,
  "discovery_report": { /* raw discovery result */ },
  "design": { /* MCPServerDesign */ },
  "generated_files": [
    { "path": "main.py", "content": "..." },
    { "path": "tools.py", "content": "..." },
    ...
  ]
}
```

**Why JSON files?**
- Simpler than database for MVP
- Projects are self-contained and portable
- Version control friendly
- Easy to debug/inspect
- No schema migrations needed

**Scalability**:
- Works well up to ~10,000 projects
- One project = one JSON file (~50KB typical)
- Directory scanning for history is O(n)
- Upgrade to PostgreSQL when projects > 100k

## Performance Considerations

### Latency Profile (Typical)

| Step | Time | Notes |
|------|------|-------|
| URL validation | 10ms | IP resolution |
| API discovery | 500-2000ms | Depends on API size |
| Analysis | 100-500ms | Endpoint parsing |
| Design (AI) | 2000-5000ms | OpenAI API call |
| Generation | 100-200ms | Jinja2 rendering |
| Validation | 50-100ms | Syntax checking |
| Storage | 50-100ms | File I/O |
| **Total** | **3-8 seconds** | End-to-end |

### Optimization Strategies

1. **Caching**
   - Cache discovered APIs by URL (5 minute TTL)
   - Reuse tool designs for similar API patterns

2. **Async I/O**
   - All HTTP requests async (httpx)
   - All file I/O async where possible
   - Parallel service calls when independent

3. **Batching**
   - Batch multiple tool designs in one GPT-4 call
   - Process multiple endpoints concurrently

4. **Resource Limits**
   - Max response size: 10MB
   - Max discovery pages: 10
   - Max redirects: 5
   - Request timeout: 20 seconds

### Concurrency

**Current Model**: Single-threaded async (Uvicorn)
- One request processed at a time
- Non-blocking I/O via async/await
- GPU-bound by OpenAI API (rate limit ~3500 RPM)

**Scaling Options**:
- Multiple Uvicorn workers (gunicorn + uvicorn)
- Rate limiting queue (Celery + Redis)
- Request queuing with priority levels

## Scalability Notes

### When to Scale

| Metric | Threshold | Action |
|--------|-----------|--------|
| Projects | 10,000+ | Move to PostgreSQL |
| Requests/min | >500 | Add load balancer + multiple workers |
| Concurrent users | >100 | Implement request queuing |
| Disk usage | >10GB | Archive old projects |
| API cost | >$500/day | Implement caching + batching |

### Architecture Changes for Scale

1. **Database**
   - PostgreSQL for projects table
   - Indexed queries for history
   - Connection pooling (sqlalchemy)

2. **Message Queue**
   - Celery for async task processing
   - Redis for caching and rate limiting
   - Separate workers for long-running tasks

3. **Distributed Caching**
   - Redis for API discovery cache
   - TTL-based invalidation
   - Cache warming for popular APIs

4. **Monitoring**
   - Prometheus metrics
   - Datadog or New Relic APM
   - Real-time alerting on errors

## Technology Choices & Trade-offs

### FastAPI (over Django, Flask)
**Choice**: FastAPI

**Why**:
- Modern, async-first
- Automatic OpenAPI documentation
- Type safety with Pydantic
- Excellent performance
- Built-in validation

**Trade-off**: Smaller ecosystem than Django

### Pydantic (over dataclasses)
**Choice**: Pydantic v2

**Why**:
- Powerful validation
- JSON schema generation
- Type coercion
- Excellent error messages

**Trade-off**: Slight performance overhead

### Jinja2 (over f-strings, mako)
**Choice**: Jinja2

**Why**:
- Industry standard
- Powerful features (filters, macros)
- Great documentation
- Performance

**Trade-off**: Learning curve, extra dependency

### JSON Files (over Database)
**Choice**: JSON files with directory structure

**Why**:
- Simplicity for MVP
- Self-contained projects
- Easy to inspect/debug

**Trade-off**: Doesn't scale beyond 10k projects, no native querying

### OpenAI GPT-4 (over Local Models)
**Choice**: OpenAI API

**Why**:
- Best at understanding APIs
- No model training needed
- Easy to iterate on prompts
- Handles edge cases well

**Trade-off**: API costs, rate limits, dependency on external service

### Vanilla JS Frontend (over React)
**Choice**: Vanilla JavaScript

**Why**:
- No build step
- Reduced dependencies
- Single HTML file
- Works offline

**Trade-off**: More DOM manipulation code, harder for complex UIs

## Error Handling Strategy

### Error Categories

1. **Validation Errors** (400)
   - Invalid URL format
   - Missing required fields
   - Oversized payloads

2. **Security Errors** (403)
   - SSRF violation
   - Blocked IP range
   - Too many redirects

3. **Discovery Errors** (422)
   - URL unreachable
   - API specification not found
   - Unsupported format

4. **Design Errors** (500)
   - GPT-4 API error
   - Invalid prompt
   - Incomplete response

5. **Generation Errors** (500)
   - Template rendering error
   - Syntax error in generated code
   - Missing dependencies

### Error Response Format

```json
{
  "success": false,
  "data": null,
  "error": "Specific error message",
  "metadata": {
    "error_code": "VALIDATION_ERROR",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

---

**Last Updated**: 2024-01-01  
**Architecture Version**: 1.0
