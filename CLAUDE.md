# MCP Server Builder – Developer Instructions

This document provides context for developers and AI agents building and maintaining the MCP Server Builder platform.

## Project Brief

**MCP Server Builder** is an AI-powered platform that transforms API documentation (URLs) into production-ready MCP (Model Context Protocol) servers through automated discovery, analysis, and code generation.

**Core Value**: Eliminates manual MCP server coding by leveraging AI to understand APIs and automatically design optimal tool interfaces.

**Built by**: Muhammad Sami Asghar Mughal (Senior AI Agent Engineer, COO at MARSA Empower)

## Architecture At A Glance

```
Frontend (HTML/Tailwind/JS)
         ↓
FastAPI Backend (Python)
    ├─ URL Validation & SSRF Protection
    ├─ API Discovery (OpenAPI/Swagger/HTML parsing)
    ├─ AI Analysis (GPT-4 for tool design)
    ├─ Code Generation (Jinja2 templates)
    └─ Project Storage (JSON files)
         ↓
Generated MCP Servers (complete Python projects)
```

## Technology Decisions & Rationale

| Component | Choice | Why |
|-----------|--------|-----|
| **Frontend** | Vanilla JS + Tailwind | Lightweight, no build step, works offline |
| **Backend** | FastAPI | Modern, fast, built-in validation (Pydantic), excellent async |
| **AI Engine** | OpenAI GPT-4 | Best at understanding APIs and designing interfaces |
| **Templates** | Jinja2 | Powerful, standard in Python ecosystem |
| **HTTP Client** | httpx | Async-ready, cleaner SSRF protection |
| **Validation** | Pydantic | Type safety, JSON schema generation |
| **Development** | Uvicorn | Fast local development, same as production |

**Explicitly NOT used**: React (overkill), Node.js (Python focus), database (JSON files OK for MVP)

## Key Files & Responsibilities

### Configuration & Setup
- **`app/config.py`** (66 lines)
  - SSRF blocklist (private/loopback IP ranges)
  - OpenAPI/Swagger detection paths
  - Environment variable loading
  - Security thresholds (timeout, max size, max discovery pages)

### Data Models (Pydantic)
- **`app/models/api.py`** (80 lines)
  - `APIRepresentation`: Normalized API structure
  - `Endpoint`: Individual API endpoint
  - `DiscoveryResult`: Output of API discovery phase
  - `Parameter`, `Response`, `SecurityScheme`: API components

- **`app/models/mcp.py`** (85 lines)
  - `MCPTool`: Single tool definition
  - `MCPServerDesign`: Complete design with all tools
  - `GeneratedMCPServer`: Generated Python code artifacts
  - `MCPProject`: Project state + all generated files

- **`app/models/project.py`** (35 lines)
  - `ProjectMetadata`: For listing/history
  - `ProjectSummary`: Minimal summary for UI
  - `HistoryResponse`: API response format

### Services (Business Logic)
Expected locations (create if missing):

- **`app/services/discovery.py`**
  - `discover_api(url: str)` – Fetch and parse documentation
  - Handle OpenAPI/Swagger detection
  - Extract endpoints, parameters, responses
  - Output: `DiscoveryResult`

- **`app/services/analyzer.py`**
  - `analyze_api(discovery_result)` – Extract structured API data
  - Normalize endpoint paths and methods
  - Identify parameter requirements and types
  - Detect authentication schemes
  - Output: `APIRepresentation`

- **`app/services/designer.py`**
  - `design_tools(api: APIRepresentation)` – AI-driven tool design
  - Call OpenAI with structured prompts
  - Generate `MCPServerDesign` with optimal tools
  - Handle tool naming, descriptions, grouping

- **`app/services/generator.py`**
  - `generate_server(design: MCPServerDesign)` – Code generation
  - Render Jinja2 templates (main.py, tools.py, etc.)
  - Validate Python syntax
  - Output: `GeneratedMCPServer`

- **`app/services/validator.py`**
  - `validate_generated_server(server: GeneratedMCPServer)` – Syntax/schema checks
  - Import validation (all dependencies available)
  - MCP schema compliance
  - Return: `ValidationResult` with errors/warnings

### Frontend
- **`index.html`** (~500 lines)
  - Single-page app: landing → builder → results
  - Sections: hero, how-it-works, features, footer
  - Uses highlight.js for code display

- **`static/client.js`** (expected)
  - Handle URL input and form submission
  - POST to `/api/discover`, `/api/analyze`, `/api/design`, `/api/generate`
  - Show progress indicators and status
  - Display generated project files
  - Download ZIP functionality

- **`static/styles.css`** (expected)
  - Tailwind CSS (CDN or compiled)
  - Dark mode support (via prefers-color-scheme)
  - Responsive design (mobile-first)

### Application Entry Point
- **`app/main.py`** (expected)
  - FastAPI app instantiation
  - CORS middleware
  - Static file serving (HTML, CSS, JS)
  - API routes: `/api/*`
  - Error handling and logging
  - Health check endpoint

## Development Workflow

### 1. Local Setup
```bash
# Create venv
python -m venv venv
source venv/bin/activate

# Install deps
pip install -r requirements.txt

# Set environment
cp .env.example .env
# Edit .env: add OPENAI_API_KEY

# Run server
uvicorn app.main:app --reload --port 8000

# Open browser
open http://localhost:8000
```

### 2. Testing During Development
```bash
# Run full test suite
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_security.py -v

# Watch mode (requires pytest-watch)
ptw

# Debug a single test
pytest tests/test_discovery.py::test_openapi_parsing -vvs
```

### 3. Code Quality
```bash
# Format code
black app/ tests/

# Import sorting
isort app/ tests/

# Type checking
mypy app/

# Lint
flake8 app/

# All together
make format lint type
```

### 4. Adding a Feature

Example: Add support for GraphQL APIs

1. **Define models** in `app/models/api.py`
   - `GraphQLSchema`, `GraphQLQuery`, etc.
   - Extend `APIRepresentation` or create new type

2. **Update discovery** in `app/services/discovery.py`
   - Add GraphQL detection logic
   - Parse GraphQL introspection schema
   - Return appropriate model

3. **Implement analysis** in `app/services/analyzer.py`
   - Extract queries/mutations from GraphQL schema
   - Map to `Endpoint`-like structures

4. **Update designer** in `app/services/designer.py`
   - Handle GraphQL in AI prompts
   - Design tools for queries vs mutations

5. **Extend generation** in `app/services/generator.py`
   - Add GraphQL client setup in generated main.py
   - Include graphql-core in requirements

6. **Write tests**
   - Unit tests for each service
   - Integration test end-to-end
   - Fixtures with sample GraphQL schemas

7. **Update documentation**
   - Add to API_REFERENCE.md
   - Update ARCHITECTURE.md
   - Note in CHANGELOG.md

## Debugging & Development Tips

### Enable Debug Logging
```python
# In app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment
DEBUG=true uvicorn app.main:app --reload
```

### Test SSRF Protection
```bash
# Should fail (blocked IP ranges)
curl -X POST http://localhost:8000/api/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "http://127.0.0.1:9000"}'

# Should succeed
curl -X POST http://localhost:8000/api/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "https://api.github.com"}'
```

### Inspect Generated MCP Server
After generation, browse `/projects/{project_id}` to:
- View generated Python files
- Test syntax with `python -m py_compile`
- Check requirements with `pip install --dry-run -r requirements.txt`

### Common Issues & Fixes

**Issue**: `OPENAI_API_KEY not found`
- **Fix**: `cp .env.example .env && edit .env` with real key

**Issue**: `ImportError: No module named 'pydantic'`
- **Fix**: `pip install -r requirements.txt` in activated venv

**Issue**: Port 8000 already in use
- **Fix**: `uvicorn app.main:app --port 8001`

**Issue**: CORS errors in browser
- **Fix**: Check `CORS_ORIGINS` in config, set to `*` for development

**Issue**: Generated server won't import
- **Fix**: Check `validator.py` output, ensure all dependencies in `requirements.txt`

## Important Architectural Decisions

### 1. JSON File Storage (Not Database)
**Decision**: Store projects as JSON files in `app/data/` instead of using database

**Rationale**:
- Simpler MVP (no DB setup/migration)
- Easy to inspect/debug projects
- Version control friendly
- Projects are self-contained (can be emailed/shared)

**Trade-off**:
- Doesn't scale to millions of projects
- No native querying/filtering
- Must load all files for history view

**When to change**: If project count > 10,000 or concurrent users > 100

### 2. OpenAI GPT-4 for Tool Design
**Decision**: Use AI to design MCP tools from API analysis, not just generate code

**Rationale**:
- AI understands API semantics better than templates
- Produces better tool names/descriptions
- Handles unusual API patterns
- Iterative improvement possible (retry with feedback)

**Trade-off**:
- Slower than pure templates (1-2 sec latency)
- Costs per generation (e.g., $0.05-0.50 per design)
- Potential inconsistency in output

**Mitigation**: Caching, validation, user editing capability

### 3. Jinja2 for Code Generation
**Decision**: Template-based code generation after AI design

**Rationale**:
- Deterministic output (same design → same code)
- Easy to modify/version templates
- Clear separation: design (AI) vs rendering (templates)

**Trade-off**:
- If AI design is wrong, generated code reflects it
- Large/complex templates are hard to maintain

**Best practice**: Keep templates simple, logic in AI prompts

### 4. Vanilla JavaScript Frontend
**Decision**: No frontend framework (React/Vue)

**Rationale**:
- Reduces dependencies
- Single HTML file deployment
- No build step
- Works in any browser without transpilation

**Trade-off**:
- More verbose DOM manipulation
- Harder to manage complex state
- Limited component reusability

**When to change**: If UI has >100 components or complex interactivity

## Performance Considerations

### Bottlenecks (Measured)
1. **OpenAI API calls** – ~2-3 seconds per design call
2. **Large API discovery** – Parsing 100+ endpoints takes ~1-2 seconds
3. **Jinja2 template rendering** – Usually <100ms even for large files
4. **Project storage** – JSON I/O is fast for small projects

### Optimization Opportunities
- **Batch AI calls**: Design multiple tools in one prompt
- **Caching**: Store discovered APIs to avoid re-fetching
- **Async**: Use async/await for all I/O operations
- **Rate limiting**: Queue requests if hitting OpenAI limits
- **Compression**: Gzip responses > 1KB

### Scalability Notes
- **Concurrent generations**: Limited by OpenAI rate limits (3500 RPM tier-1)
- **Project storage**: 1GB disk ~= 10,000 medium projects
- **Memory**: FastAPI + Uvicorn uses ~100MB baseline
- **Database**: Move to PostgreSQL/MongoDB when projects > 100k

## Security Guidelines

### What We Protect Against
1. **SSRF attacks** – Block private IP ranges (127.x, 10.x, 192.168.x, etc.)
2. **Large response DOS** – Max 10MB response body
3. **URL bombing** – Max 10 discovery pages
4. **Redirect loops** – Max 5 redirects per request
5. **API key exposure** – Never log API keys, only env vars
6. **Code injection** – Sanitize API responses before templating
7. **Malicious generated code** – Validate syntax before returning

### What NOT to do
- ❌ Log API keys or sensitive data
- ❌ Store credentials in code or config files
- ❌ Trust user input without validation
- ❌ Disable HTTPS in production
- ❌ Commit .env files
- ❌ Run generated code without review
- ❌ Expose internal error details to clients

See `SECURITY.md` for detailed security architecture.

## Testing Requirements

### Unit Tests
- One test file per service
- Test happy path and error cases
- Mock external APIs (OpenAI, HTTP requests)
- Aim for 80%+ coverage

### Integration Tests
- Test full pipeline (URL → generated server)
- Use fixture APIs (httpbin, swaggerhub examples)
- Validate generated code syntax
- Check project storage/retrieval

### Security Tests
- SSRF protection (blocked IPs, redirects)
- URL validation (format, length, encoding)
- API key handling (never exposed in logs)
- Generated code doesn't include secrets

### Manual Testing
- Test with real APIs (GitHub, Stripe, Twilio)
- Verify generated servers run without errors
- Check MCP compatibility with Claude Desktop
- Test on Windows/Mac/Linux

See `TESTING.md` for complete testing guide.

## Deployment Notes

### Development
```bash
uvicorn app.main:app --reload --port 8000
```

### Staging/Production
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --env PYTHONUNBUFFERED=1
```

### Environment Variables (Production)
```bash
export OPENAI_API_KEY=sk-...
export DEBUG=false
export CORS_ORIGINS=https://example.com
export REQUEST_TIMEOUT=30
export LOG_LEVEL=INFO
```

### Monitoring
- Health check: `GET /health`
- Metrics: Log generation times, success/fail rates
- Errors: Alert on 500+ errors
- Usage: Track API calls per hour, top source URLs

See `DEPLOYMENT.md` for full production guide.

## Common Tasks & How To Do Them

### Add a New API Endpoint
1. Define request model: `class DiscoverRequest(BaseModel):`
2. Define response model: `class DiscoverResponse(BaseModel):`
3. Create route: `@app.post("/api/discover")`
4. Call service: `result = await discover_api(request.url)`
5. Return response: `return DiscoverResponse(...)`
6. Write tests: `test_discover_valid_url()`, `test_discover_invalid_url()`

### Update Jinja2 Template
1. Find template file in `templates/`
2. Make edit (e.g., add new parameter)
3. Test with: `python -m jinja2.env`
4. Run generator: `pytest tests/test_generation.py`
5. Inspect generated output for correctness

### Change the AI Prompt
1. Find prompt in `app/services/designer.py`
2. Update system message or user message
3. Run test with fixed API: `pytest tests/test_designer.py::test_design_tools`
4. Review generated tool designs for quality
5. Iterate if needed

### Add Support for New API Format
1. Extend `APIRepresentation` or create new model
2. Update `discovery.py` to detect new format
3. Add parsing logic to extract endpoints
4. Add test with sample API of that format
5. Update documentation (API_REFERENCE.md, ARCHITECTURE.md)

### Debug a Generated Server
1. Find project in `app/data/{project_id}.json`
2. Extract main.py, check syntax: `python -m py_compile`
3. Try importing: `python -c "import sys; sys.path.insert(0, 'project'); import main"`
4. Check requirements: `pip install --dry-run -r requirements.txt`
5. Run: `python project/main.py`

## Version & Releases

Current version: Read from `app/__version__.py`

Release process:
1. Update version in `app/__version__.py`
2. Update `CHANGELOG.md` with changes
3. Create git tag: `git tag v0.2.0`
4. Push: `git push origin main --tags`
5. GitHub Actions creates release + uploads artifacts

## Useful Commands

```bash
# Format code
make format

# Run tests
make test

# Type check
make type

# Full lint + type + format
make all

# Build for production
make build

# Start dev server
make dev

# Clean artifacts
make clean
```

(See Makefile if it exists, or run commands manually)

## Key Metrics to Track

- **Generation time**: Target <5 seconds per project
- **Success rate**: Target >95% (captures all endpoints)
- **API key cost**: Monitor GPT-4 usage
- **Project storage**: Clean up old projects monthly
- **Error rate**: Alert if >1% of requests fail
- **User satisfaction**: Track generated server usability

## Future Work / Technical Debt

- [ ] Add GraphQL support (currently REST/OpenAPI only)
- [ ] Implement caching for discovered APIs
- [ ] Add database (PostgreSQL) for scalability
- [ ] Build CLI tool for headless generation
- [ ] Add webhook support for generated servers
- [ ] Implement server one-click hosting
- [ ] Add rate limiting on endpoints
- [ ] Improve AI prompts for edge cases
- [ ] Support multi-API composition
- [ ] Add automated testing for generated servers

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **OpenAI API**: https://platform.openai.com/docs/
- **MCP Spec**: https://modelcontextprotocol.io/
- **Tailwind CSS**: https://tailwindcss.com/
- **Jinja2**: https://jinja.palletsprojects.com/

---

**Last Updated**: 2024-01-01  
**Maintained By**: Muhammad Sami Asghar Mughal
