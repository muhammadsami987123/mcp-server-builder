# MCP Tool Designer & Generator Guide

This document explains the MCP tool design and generation engine.

## Architecture Overview

```
Normalized API (APIRepresentation)
  ↓
MCP Designer (mcp_designer.py)
  ├─ Analyze API structure
  ├─ Call GPT-4 mini for tool design
  └─ Generate MCPServerDesign
  ↓
MCP Generator (mcp_generator.py)
  ├─ Generate server.py (MCP server init)
  ├─ Generate config.py (configuration)
  ├─ Generate client.py (API client)
  ├─ Generate models.py (Pydantic models)
  ├─ Generate tools/api_tools.py (tool implementations)
  ├─ Generate requirements.txt
  ├─ Generate .env.example
  ├─ Generate README.md
  ├─ Generate mcp-config.json
  └─ Generate pyproject.toml
  ↓
Validator (validator.py)
  ├─ Check file structure
  ├─ Validate Python syntax
  ├─ Verify MCP configuration
  ├─ Validate tool schemas
  └─ Generate validation report
  ↓
Project Manager (project_manager.py)
  ├─ Create ZIP file for download
  ├─ Count lines of code
  ├─ Build file tree
  └─ Extract individual files
  ↓
Integration Pipeline (integration.py)
  └─ Orchestrate complete generation flow
```

## Services

### 1. MCPDesigner (`mcp_designer.py`)

Intelligent MCP tool design using OpenAI GPT-4 mini.

**Key Responsibilities:**
- Analyze normalized API representation
- Call OpenAI to design useful MCP tools
- Validate AI response using Pydantic
- Handle failures gracefully with fallback design
- Map API endpoints to MCP tools

**Main Class:** `MCPDesigner`

**Key Methods:**
- `design_tools(api: APIRepresentation) -> MCPServerDesign` - Design tools from API

**Example Usage:**
```python
from app.services.mcp_designer import MCPDesigner
from app.models.api import APIRepresentation

designer = MCPDesigner()
design = designer.design_tools(api_representation)

print(f"Designed {len(design.tools)} tools")
for tool in design.tools:
    print(f"- {tool.name}: {tool.description}")
```

**AI Prompt Strategy:**
- Summarizes API to stay within token limits
- Asks for structured JSON output
- Validates response against Pydantic models
- Retries on failure with structured correction

**Fallback Design:**
- If AI parsing fails, creates a simple design
- Maps each endpoint to a tool
- Handles common patterns (path parameters, method prefixes)

### 2. MCPServerGenerator (`mcp_generator.py`)

Generates complete Python MCP server projects.

**Key Responsibilities:**
- Generate `src/server.py` - MCP server initialization
- Generate `src/config.py` - Configuration management
- Generate `src/client.py` - API client for calling endpoints
- Generate `src/models.py` - Pydantic response models
- Generate `src/tools/api_tools.py` - Tool implementations
- Generate supporting files (requirements, .env.example, etc.)
- Use proper project structure and best practices

**Main Class:** `MCPServerGenerator`

**Key Methods:**
- `generate_project(design: MCPServerDesign) -> Dict[str, str]` - Generate all files

**Generated Files:**
```
src/
├── server.py          - MCP server with tool registration
├── config.py          - Config management with env vars
├── client.py          - HTTP client for API calls
├── models.py          - Pydantic response models
└── tools/
    ├── __init__.py
    └── api_tools.py   - Tool definitions and handlers

.env.example           - Template for environment variables
.gitignore             - Git ignore patterns
requirements.txt       - Python dependencies
README.md              - Professional documentation
mcp-config.json        - MCP client configuration example
pyproject.toml         - Project metadata
```

**Code Quality Features:**
- Type hints throughout
- Proper error handling
- Modular tool files
- Centralized configuration
- Environment variable support
- Secure (no hardcoded secrets)
- Comments for non-obvious logic

**Example Usage:**
```python
from app.services.mcp_generator import MCPServerGenerator

generator = MCPServerGenerator()
files = generator.generate_project(design)

for filepath, content in files.items():
    print(f"{filepath}: {len(content)} bytes")
```

### 3. AutoReadmeGenerator (`auto_readme.py`)

Automatically generates professional README files.

**Key Responsibilities:**
- Generate comprehensive documentation
- Include installation instructions
- Document all available tools
- Provide configuration examples
- Include troubleshooting section
- Add MCP client configuration examples

**Main Class:** `AutoReadmeGenerator`

**Key Methods:**
- `generate(design: MCPServerDesign) -> str` - Generate README

**Sections Generated:**
- Header and overview
- Requirements
- Installation instructions
- Environment setup
- Configuration guide
- Running instructions
- Available tools documentation
- Authentication setup
- MCP client configuration
- Usage examples
- Troubleshooting
- Support information

**Example Usage:**
```python
from app.services.auto_readme import AutoReadmeGenerator

generator = AutoReadmeGenerator()
readme_content = generator.generate(design)

print(readme_content)
```

### 4. MCPServerValidator (`validator.py`)

Validates generated MCP servers comprehensively.

**Key Responsibilities:**
- Verify project file structure
- Validate Python syntax
- Check MCP configuration
- Validate tool input schemas
- Verify requirements.txt
- Check environment configuration
- Validate README
- Generate validation report

**Main Class:** `MCPServerValidator`

**Validation Report Example:**
```
Validation Report
==================================================

✓ File exists: src/server.py
✓ Python syntax valid: src/server.py
✓ MCP server configured in mcp-config.json
✓ Tool name valid: list_users
✓ Tool schema valid: list_users
✓ Environment variable template: API_BASE_URL
✓ README includes 'Installation' section

⚠ Package 'mcp' not found in requirements.txt
⚠ README missing 'Configuration' section

✗ Missing required file: tests/test_tools.py

==================================================
7 passed, 2 warnings, 1 errors
```

**Validation Checks:**
1. **Structure** - All required files present
2. **Python Syntax** - Valid Python code
3. **MCP Config** - Valid JSON, proper structure
4. **Tool Schemas** - Valid JSON schemas, proper naming
5. **Requirements** - Critical packages included
6. **Environment** - Template variables defined
7. **README** - Includes essential sections
8. **Imports** - Resolvable dependencies

**Example Usage:**
```python
from app.services.validator import MCPServerValidator

validator = MCPServerValidator()
result = validator.validate_project(files, design)

print(result.to_string())
print(f"Success: {result.to_dict()['success']}")
```

### 5. ProjectManager (`project_manager.py`)

Manages project files and downloads.

**Key Responsibilities:**
- Create ZIP files for download
- Save projects locally
- Count lines of code
- Generate file tree structure
- Extract files from ZIP
- Validate file structure
- Create project metadata

**Main Class:** `ProjectManager`

**Key Methods:**
- `create_zip(files: Dict[str, str], project_name: str) -> io.BytesIO` - Create downloadable ZIP
- `save_project_locally(files, base_path, project_name) -> Path` - Save to disk
- `count_lines_of_code(files) -> Dict[str, int]` - Count LOC by file type
- `get_file_tree(files) -> Dict` - Build file tree structure
- `create_project_metadata(design, files, validation) -> Dict` - Generate metadata

**Example Usage:**
```python
from app.services.project_manager import ProjectManager

manager = ProjectManager()

# Create ZIP for download
zip_buffer = manager.create_zip(files, "my_mcp_server")

# Count lines of code
loc = manager.count_lines_of_code(files)
print(f"Total: {loc['total']} lines")
print(f"Python: {loc['python']} lines")

# Get file tree
tree = manager.get_file_tree(files)
print(tree)
```

### 6. MCPGenerationPipeline (`integration.py`)

Orchestrates the complete generation pipeline.

**Key Responsibilities:**
- Coordinate all generation steps
- Manage generation status
- Create project summaries
- Generate tool documentation
- Support regeneration with options
- Track progress through stages

**Main Classes:**
- `MCPGenerationPipeline` - Main orchestrator
- `GenerationStatus` - Track progress

**Stages:**
1. api_discovery - Fetch and analyze API
2. api_analysis - Extract structure and patterns
3. tool_design - AI-powered tool design
4. code_generation - Generate server files
5. validation - Validate generated code

**Example Usage:**
```python
from app.services.integration import MCPGenerationPipeline

pipeline = MCPGenerationPipeline()

# Generate complete project
design, files, validation = pipeline.generate_complete_project(
    api=api_representation,
    api_discovery_report=discovery_report
)

# Create download ZIP
zip_buffer = pipeline.create_download_zip(files, design.server_name)

# Get project summary
summary = pipeline.get_project_summary(design, files, validation)
print(f"Generated {summary['tools']['total']} tools")

# Regenerate with custom options
design2, files2, validation2 = pipeline.regenerate_with_options(
    api=api_representation,
    design=design,
    options={
        "server_name": "my_custom_name",
        "selected_tools": ["list_users", "get_user"],
    }
)
```

## Integration with Backend

### In FastAPI Routes

```python
from fastapi import FastAPI, HTTPException
from app.services.integration import MCPGenerationPipeline
from app.models.api import APIRepresentation

app = FastAPI()
pipeline = MCPGenerationPipeline()

@app.post("/api/generate")
async def generate_server(api: APIRepresentation):
    try:
        design, files, validation = pipeline.generate_complete_project(
            api=api,
            api_discovery_report=None
        )
        
        return {
            "success": True,
            "server_name": design.server_name,
            "tools_count": len(design.tools),
            "validation": validation,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/project/{project_id}/download")
async def download_project(project_id: str):
    # Retrieve design and files from storage
    design = load_design(project_id)
    files = load_files(project_id)
    
    zip_buffer = pipeline.create_download_zip(
        files, 
        design.server_name
    )
    
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={design.server_name}.zip"
        }
    )
```

## Configuration

All services use environment variables defined in `app/config.py`:

```python
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview  # or gpt-4.1-mini
REQUEST_TIMEOUT=20
MAX_RESPONSE_SIZE=10485760  # 10MB
```

## Error Handling

All services implement proper error handling:

1. **MCPDesigner**
   - JSON parsing errors → fallback design
   - OpenAI API errors → retry with backoff
   - Pydantic validation errors → attempt correction

2. **MCPServerGenerator**
   - Template rendering errors → detailed error message
   - File path issues → resolved automatically

3. **Validator**
   - Syntax errors → detailed error reporting
   - Missing files → identified with severity level
   - Schema issues → specific validation messages

## Testing

Example test for the generator:

```python
from app.services.integration import MCPGenerationPipeline
from app.services.examples import get_example_github_api

pipeline = MCPGenerationPipeline()
api = get_example_github_api()

# Generate
design, files, validation = pipeline.generate_complete_project(api)

# Validate
assert validation['success'] == True
assert len(design.tools) > 0
assert 'src/server.py' in files
assert 'requirements.txt' in files

# Create ZIP
zip_buffer = pipeline.create_download_zip(files, design.server_name)
assert zip_buffer.getbuffer().nbytes > 0

print("All tests passed!")
```

## Token Efficiency

The designer minimizes token usage:

1. **API Summary** - Only sends essential endpoint information
2. **Endpoint Limit** - Limits to first 50 endpoints for large APIs
3. **Structured Output** - Asks for JSON to avoid parsing text
4. **Focused Prompt** - Includes only relevant context

For a typical API with 50 endpoints:
- Input tokens: 2,000-3,000
- Output tokens: 1,000-2,000
- Total: ~4,000-5,000 tokens (~$0.08)

## Extending the System

### Add a New Validation Check

```python
# In validator.py
class MCPServerValidator:
    def _validate_security(self, files: Dict[str, str]):
        """Validate security best practices."""
        server_py = files.get("src/server.py", "")
        
        if "password" in server_py.lower():
            self.result.add_warning("Hardcoded password detected")
        
        if ".env" not in files:
            self.result.add_error("Missing .env configuration")
```

### Add a New Code Generation Template

```python
# In mcp_generator.py
class MCPServerGenerator:
    def _generate_docker_file(self, design: MCPServerDesign) -> str:
        """Generate Dockerfile for containerization."""
        return f"""FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ src/
CMD ["python", "src/server.py"]
"""
```

### Add a New Service

```python
# In integration.py
from app.services.docker_builder import DockerBuilder

class MCPGenerationPipeline:
    def __init__(self):
        self.designer = MCPDesigner()
        self.generator = MCPServerGenerator()
        self.validator = MCPServerValidator()
        self.docker_builder = DockerBuilder()  # New!
```

## Performance Considerations

1. **AI Generation** - Most time-consuming (1-3 seconds per API)
2. **File Generation** - Fast (< 500ms)
3. **Validation** - Fast (< 200ms)
4. **ZIP Creation** - Fast (< 100ms)

Total for typical API: 2-4 seconds

## Security

All generated servers:
- Never hardcode credentials
- Use environment variables for secrets
- Include .gitignore to protect .env files
- Provide secure examples in .env.example
- Validate all inputs through Pydantic

The generated servers are production-ready from a security perspective.

## References

- MCP Specification: https://spec.modelcontextprotocol.io/
- OpenAI API: https://platform.openai.com/docs/api-reference
- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/
