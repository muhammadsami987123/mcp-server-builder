# Testing – MCP Server Builder Test Guide

Complete guide to testing MCP Server Builder, including structure, execution, and coverage goals.

## Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_security.py -v

# Run specific test
pytest tests/test_security.py::test_ssrf_blocks_loopback -v

# Watch mode (install: pip install pytest-watch)
ptw

# Only fast tests (skip slow/integration)
pytest -m "not slow and not integration"
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                          # Shared fixtures
├── test_security.py                     # SSRF, URL validation
├── test_discovery.py                    # API discovery
├── test_analyzer.py                     # Endpoint analysis
├── test_designer.py                     # MCP tool design
├── test_generator.py                    # Code generation
├── test_validator.py                    # Code validation
├── test_integration.py                  # E2E pipeline
├── fixtures/
│   ├── __init__.py
│   ├── sample_openapi.json              # OpenAPI 3.0 example
│   ├── sample_swagger.json              # Swagger 2.0 example
│   ├── sample_html_docs.html            # HTML documentation
│   └── mock_responses.py                # Mock HTTP responses
└── mock_apis/
    ├── server.py                        # Local mock API server
    └── schemas/                         # OpenAPI/Swagger fixtures
```

## Testing Pyramid

```
                    /\
                   /  \
                  / E2E \          < 5%  (integration)
                 /--------\
                /          \
               /   Unit     \     70-80% (fast, isolated)
              /              \
             /   Integration  \   15-25% (moderate speed)
            /--------------------\
```

### Unit Tests (70-80% of tests)

**Focus**: Individual services in isolation

**Examples**:
- URL validation logic
- Parameter extraction
- Template rendering
- File I/O

**Mock Dependencies**:
```python
# tests/test_discovery.py
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_openapi_detection():
    mock_response = '{"openapi": "3.0.0", "paths": {}}'
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.text = mock_response
        result = await discover_api('https://example.com')
        assert result.detected_type == 'openapi3'
```

### Integration Tests (15-25% of tests)

**Focus**: Multiple services working together

**Examples**:
- Discovery → Analysis → Design pipeline
- End-to-end URL → MCP server generation
- Error handling across services

**Use Real or Fixture APIs**:
```python
# tests/test_integration.py
@pytest.mark.integration
async def test_full_pipeline_with_fixture_api():
    url = 'http://localhost:8888/openapi.json'  # Local fixture
    result = await discover_api(url)
    api = await analyze_api(result)
    design = await design_tools(api)
    server = await generate_server(design)
    assert server.main_file is not None
    assert len(server.main_file) > 0
```

### E2E Tests (<5% of tests)

**Focus**: Complete user workflow

**Skip in CI** (slow, external dependencies):
```python
# tests/test_integration.py
@pytest.mark.slow
async def test_generate_real_api_github():
    """Test against real GitHub API (skip in CI)"""
    result = await discover_api('https://api.github.com')
    assert result.success
    assert len(result.api.endpoints) > 0
```

## Test Categories

### 1. Security Tests

**Location**: `tests/test_security.py`

**Coverage**:
- SSRF protection (blocked IPs)
- URL validation (format, length)
- Redirect handling (max 5 hops)
- Response size limits
- API key handling

**Examples**:

```python
import pytest
from app.services.security import validate_url, is_safe_ip

class TestSSRFProtection:
    """Test SSRF protection"""
    
    @pytest.mark.parametrize("ip,expected", [
        ("127.0.0.1", False),           # Loopback
        ("192.168.1.1", False),         # Private
        ("10.0.0.1", False),            # Private
        ("172.16.0.1", False),          # Private
        ("8.8.8.8", True),              # Public (allowed)
        ("1.1.1.1", True),              # Public (allowed)
    ])
    def test_ip_blocklist(self, ip, expected):
        assert is_safe_ip(ip) == expected
    
    def test_url_must_be_https(self):
        with pytest.raises(ValueError):
            validate_url("http://example.com")  # Reject HTTP
    
    async def test_redirect_limit(self):
        """Test max 5 redirects"""
        with patch('httpx.AsyncClient.get') as mock:
            mock.side_effect = [
                Response(status_code=301),  # Redirect 1
                Response(status_code=301),  # Redirect 2
                Response(status_code=301),  # Redirect 3
                Response(status_code=301),  # Redirect 4
                Response(status_code=301),  # Redirect 5
                Response(status_code=301),  # Redirect 6 – BLOCKED
            ]
            with pytest.raises(TooManyRedirectsError):
                await fetch_url("https://example.com")

class TestAPIKeyHandling:
    """Test API key security"""
    
    def test_api_key_not_logged(self, caplog):
        """Ensure API keys never appear in logs"""
        with caplog.at_level(logging.DEBUG):
            client = OpenAIClient(api_key="sk-secret123")
            # Do something...
        assert "sk-secret" not in caplog.text
        assert "secret123" not in caplog.text
```

### 2. Discovery Tests

**Location**: `tests/test_discovery.py`

**Coverage**:
- OpenAPI 3.0 parsing
- Swagger 2.0 parsing
- HTML documentation extraction
- Link following
- Edge cases (malformed specs, missing fields)

**Examples**:

```python
class TestOpenAPIParsing:
    """Test OpenAPI 3.0 discovery"""
    
    async def test_detect_openapi_json(self):
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "My API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            }
        }
        result = await discover_api_from_spec(spec)
        assert result.detected_type == "openapi3"
        assert len(result.api.endpoints) == 1
        assert result.api.endpoints[0].path == "/users"
    
    async def test_find_openapi_in_common_paths(self):
        """Test finding OpenAPI spec in common locations"""
        with patch('discover_api_from_url') as mock:
            mock.return_value = DiscoveryResult(...)
            
            # Should try these paths
            paths = ["/openapi.json", "/swagger.json", "/api/openapi.json"]
            # Implementation should try each in order
    
    async def test_parse_malformed_spec(self):
        """Test graceful handling of malformed specs"""
        malformed = '{"openapi": "3.0.0", broken json'
        result = parse_openapi_spec(malformed)
        assert not result.success
        assert "JSON" in result.errors[0]

class TestSwagger2Parsing:
    """Test Swagger 2.0 discovery"""
    
    async def test_detect_swagger_json(self):
        spec = {
            "swagger": "2.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/items": {
                    "get": {
                        "summary": "Get items",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        result = await discover_api_from_spec(spec)
        assert result.detected_type == "swagger2"
```

### 3. Analysis Tests

**Location**: `tests/test_analyzer.py`

**Coverage**:
- Endpoint extraction
- Parameter parsing
- Response schema extraction
- Authentication detection
- Tag/category grouping

**Examples**:

```python
class TestEndpointExtraction:
    """Test endpoint parsing"""
    
    async def test_extract_all_methods(self):
        """Test extracting all HTTP methods"""
        api = APIRepresentation(
            endpoints=[
                Endpoint(path="/items", method="GET"),
                Endpoint(path="/items", method="POST"),
                Endpoint(path="/items/{id}", method="PUT"),
                Endpoint(path="/items/{id}", method="DELETE"),
            ]
        )
        endpoints = await analyze_endpoints(api)
        assert len(endpoints) == 4
        methods = {e.method for e in endpoints}
        assert methods == {"GET", "POST", "PUT", "DELETE"}
    
    async def test_normalize_path_parameters(self):
        """Test path parameter extraction"""
        endpoint = Endpoint(
            path="/users/{userId}/posts/{postId}",
            method="GET"
        )
        params = extract_path_params(endpoint)
        assert {p.name for p in params} == {"userId", "postId"}
        assert all(p.in_ == "path" for p in params)
    
    async def test_detect_authentication(self):
        """Test auth scheme detection"""
        api = APIRepresentation(
            security_schemes={
                "api_key": SecurityScheme(type="apiKey", scheme="bearer"),
                "oauth2": SecurityScheme(type="oauth2", flows={"implicit": {}})
            }
        )
        assert api.authentication_required is True
        assert "bearer" in api.authentication_type
```

### 4. Designer Tests

**Location**: `tests/test_designer.py`

**Coverage**:
- Prompt generation
- GPT-4 response parsing
- Tool schema validation
- Error handling

**Examples**:

```python
class TestToolDesign:
    """Test MCP tool design"""
    
    @pytest.mark.asyncio
    async def test_design_tools_from_api(self):
        """Test tool design from API representation"""
        api = APIRepresentation(
            name="UserAPI",
            endpoints=[
                Endpoint(path="/users", method="GET", summary="List users"),
                Endpoint(path="/users/{id}", method="GET", summary="Get user"),
                Endpoint(path="/users", method="POST", summary="Create user"),
            ]
        )
        
        with patch('openai.ChatCompletion.create') as mock_gpt:
            mock_gpt.return_value.choices[0].message.content = json.dumps({
                "tools": [
                    {
                        "name": "list_users",
                        "description": "Retrieve all users",
                        "api_endpoint": "GET /users",
                        "parameters": []
                    },
                    {
                        "name": "get_user",
                        "description": "Get a specific user",
                        "api_endpoint": "GET /users/{id}",
                        "parameters": [{"name": "id", "type": "string"}]
                    }
                ]
            })
            
            design = await design_tools(api)
            assert len(design.tools) >= 2
            assert any(t.name == "list_users" for t in design.tools)
```

### 5. Generator Tests

**Location**: `tests/test_generator.py`

**Coverage**:
- Template rendering
- Python syntax validation
- File generation
- Dependency completeness

**Examples**:

```python
class TestCodeGeneration:
    """Test MCP server code generation"""
    
    async def test_generate_main_file(self):
        """Test main.py generation"""
        design = MCPServerDesign(
            server_name="test_server",
            server_description="Test MCP Server",
            tools=[
                MCPTool(
                    name="get_data",
                    description="Fetch data",
                    api_endpoint="GET /data",
                    method="GET",
                    path="/data",
                    parameters=[],
                    input_schema=ToolInputSchema()
                )
            ],
            api_base_url="https://api.example.com",
            source_api_name="Example API"
        )
        
        server = await generate_server(design)
        assert server.main_file is not None
        assert "class MCPServer" in server.main_file or "@app.tool" in server.main_file
        assert "get_data" in server.main_file
    
    def test_generated_code_is_valid_python(self):
        """Test generated code has valid Python syntax"""
        code = generate_main_py(design)
        try:
            compile(code, 'main.py', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")
    
    async def test_requirements_file_has_all_deps(self):
        """Test requirements.txt includes all dependencies"""
        server = await generate_server(design)
        requirements = server.requirements_file.split('\n')
        
        # Should include core MCP deps
        assert any('mcp' in r for r in requirements)
        assert any('pydantic' in r for r in requirements)
```

### 6. Validator Tests

**Location**: `tests/test_validator.py`

**Coverage**:
- Syntax validation
- Import checking
- MCP schema compliance
- Dependency availability

**Examples**:

```python
class TestValidation:
    """Test generated server validation"""
    
    async def test_validate_syntax(self):
        """Test Python syntax validation"""
        valid_code = "def hello(): return 'world'"
        result = validate_syntax(valid_code)
        assert result.valid is True
        
        invalid_code = "def hello( return 'world'"
        result = validate_syntax(invalid_code)
        assert result.valid is False
        assert len(result.errors) > 0
    
    async def test_validate_imports(self):
        """Test import availability checking"""
        code_with_available = "from pydantic import BaseModel"
        result = validate_imports(code_with_available)
        assert result.valid is True
        
        code_with_unavailable = "from nonexistent_module import Something"
        result = validate_imports(code_with_unavailable)
        assert result.valid is False
```

## Running Tests in CI/CD

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.8", "3.9", "3.10", "3.11"]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run tests
      run: pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
```

## Coverage Goals

**Target**: 80%+ line coverage

**By Module**:
- `services/` – 90%+ (critical business logic)
- `models/` – 100% (data validation)
- `utils/` – 85%+ (utilities)
- `main.py` – 75%+ (route handlers)

**How to Check**:

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# Open in browser
open htmlcov/index.html

# Get summary
pytest --cov=app --cov-report=term
```

## Best Practices

### 1. Use Fixtures for Reusable Data

```python
# conftest.py
@pytest.fixture
def sample_api():
    return APIRepresentation(
        name="Test API",
        endpoints=[
            Endpoint(path="/users", method="GET"),
            Endpoint(path="/users/{id}", method="GET"),
        ]
    )

# In test
def test_something(sample_api):
    result = analyze_api(sample_api)
    assert len(result.endpoints) == 2
```

### 2. Mock External Dependencies

```python
# Don't make real API calls
with patch('openai.ChatCompletion.create') as mock:
    mock.return_value.choices[0].message.content = '{"tools": []}'
    result = await design_tools(api)
```

### 3. Test Both Happy Path and Errors

```python
def test_happy_path():
    result = validate_url("https://example.com")
    assert result is True

def test_invalid_format():
    with pytest.raises(ValueError):
        validate_url("not a url")

def test_blocked_ip():
    with pytest.raises(SecurityError):
        validate_url("http://127.0.0.1")
```

### 4. Use Parametrize for Multiple Cases

```python
@pytest.mark.parametrize("ip,expected", [
    ("127.0.0.1", False),
    ("192.168.1.1", False),
    ("8.8.8.8", True),
])
def test_ip_validation(ip, expected):
    assert is_safe_ip(ip) == expected
```

### 5. Test Async Code Properly

```python
@pytest.mark.asyncio
async def test_async_discovery():
    result = await discover_api("https://api.example.com")
    assert result.success
```

## Debugging Tests

### Print Debug Info

```python
def test_something(caplog):
    with caplog.at_level(logging.DEBUG):
        # ... test code
    print(caplog.text)  # See all logs
```

### Run Single Test with Verbose Output

```bash
pytest tests/test_security.py::test_ssrf_blocks_loopback -vvs
```

### Use pytest-watch for TDD

```bash
ptw  # Automatically re-runs tests when files change
```

### Add Breakpoints

```python
def test_something():
    result = do_something()
    breakpoint()  # Debugger stops here
    assert result is not None
```

## Fixture APIs for Testing

### Local Mock API Server

```python
# tests/mock_apis/server.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/openapi.json")
def get_openapi():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Mock API", "version": "1.0.0"},
        "paths": {...}
    }

# In test
@pytest.fixture
def mock_server():
    import subprocess
    proc = subprocess.Popen(["python", "-m", "uvicorn", "tests.mock_apis.server:app"])
    yield "http://localhost:8000"
    proc.terminate()
```

---

**Last Updated**: 2024-01-01
