# MCP Generator - Quick API Reference

Fast lookup for integrating the MCP generation services into your FastAPI backend.

## Import Statements

```python
# Core generation
from app.services.integration import MCPGenerationPipeline, GenerationStatus
from app.services.mcp_designer import MCPDesigner
from app.services.mcp_generator import MCPServerGenerator
from app.services.validator import MCPServerValidator
from app.services.project_manager import ProjectManager
from app.services.auto_readme import AutoReadmeGenerator

# Models
from app.models.api import APIRepresentation, Endpoint
from app.models.mcp import MCPServerDesign, MCPTool

# Examples
from app.services.examples import (
    get_example_github_api,
    get_example_weather_api,
    get_example_stripe_api,
)
```

## Pipeline (Recommended)

Use the pipeline for the complete flow:

```python
from app.services.integration import MCPGenerationPipeline

pipeline = MCPGenerationPipeline()

# Generate complete project
design, files, validation = pipeline.generate_complete_project(
    api=api_representation,
    api_discovery_report=discovery_report  # optional
)

# Create ZIP for download
zip_buffer = pipeline.create_download_zip(files, design.server_name)

# Get summary
summary = pipeline.get_project_summary(design, files, validation)

# Generate tool docs
tool_docs = pipeline.get_tool_documentation(design)

# Regenerate with options
design2, files2, val2 = pipeline.regenerate_with_options(
    api=api_representation,
    design=design,
    options={"server_name": "custom_name", "selected_tools": [...]}
)

# Create project metadata
project = pipeline.create_project_metadata(design, files, discovery_report)
```

## Individual Services

Use individual services for more control:

### MCP Designer

```python
from app.services.mcp_designer import MCPDesigner

designer = MCPDesigner()
design = designer.design_tools(api_representation)

# design.server_name
# design.server_description
# design.tools -> List[MCPTool]
```

### Server Generator

```python
from app.services.mcp_generator import MCPServerGenerator

generator = MCPServerGenerator()
files = generator.generate_project(design)

# files is Dict[str, str] with all file contents
# Keys: "src/server.py", "src/config.py", etc.
```

### Validator

```python
from app.services.validator import MCPServerValidator

validator = MCPServerValidator()
result = validator.validate_project(files, design)

# result.passed -> List[str]
# result.warnings -> List[str]
# result.errors -> List[str]
# result.to_dict() -> validation report
# result.to_string() -> readable output
```

### Project Manager

```python
from app.services.project_manager import ProjectManager

# Create ZIP
zip_buffer = ProjectManager.create_zip(files, project_name)

# Save to disk
project_path = ProjectManager.save_project_locally(
    files, 
    Path("./projects"),
    project_name
)

# Count lines of code
loc = ProjectManager.count_lines_of_code(files)
# loc["total"], loc["python"], loc["markdown"], etc.

# Get file tree
tree = ProjectManager.get_file_tree(files)

# Validate structure
issues = ProjectManager.validate_file_structure(files)
```

### README Generator

```python
from app.services.auto_readme import AutoReadmeGenerator

generator = AutoReadmeGenerator()
readme = generator.generate(design)
```

## FastAPI Integration Examples

### Basic Generation Endpoint

```python
from fastapi import FastAPI, HTTPException
from app.services.integration import MCPGenerationPipeline

app = FastAPI()
pipeline = MCPGenerationPipeline()

@app.post("/api/generate")
async def generate_server(api: APIRepresentation):
    try:
        design, files, validation = pipeline.generate_complete_project(api)
        
        return {
            "success": True,
            "server_name": design.server_name,
            "tools_count": len(design.tools),
            "validation": validation,
            "status": "ready_for_download",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Download Endpoint

```python
from fastapi.responses import StreamingResponse

@app.get("/api/project/{project_id}/download")
async def download_project(project_id: str):
    # Retrieve from storage
    design = storage.get_design(project_id)
    files = storage.get_files(project_id)
    
    # Create ZIP
    zip_buffer = pipeline.create_download_zip(files, design.server_name)
    
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={design.server_name}.zip"
        }
    )
```

### Status Endpoint

```python
from app.services.integration import GenerationStatus

status_tracker = GenerationStatus()

@app.get("/api/project/{project_id}/status")
async def get_status(project_id: str):
    status = load_status(project_id)
    return status.to_dict()
```

### Regeneration Endpoint

```python
@app.post("/api/project/{project_id}/regenerate")
async def regenerate_project(project_id: str, options: dict):
    # Load original
    design = storage.get_design(project_id)
    api = storage.get_api(project_id)
    
    # Regenerate
    design2, files2, val2 = pipeline.regenerate_with_options(
        api=api,
        design=design,
        options=options
    )
    
    # Save new version
    storage.save_design(project_id, design2)
    storage.save_files(project_id, files2)
    
    return {
        "success": True,
        "server_name": design2.server_name,
        "tools_count": len(design2.tools),
    }
```

## Validation Usage

```python
# Get validation result
result = validator.validate_project(files, design)

# Check if valid
if result.to_dict()["success"]:
    print("✓ Project is valid")
else:
    print("✗ Project has errors:")
    for error in result.errors:
        print(f"  - {error}")

# Show to user
print(result.to_string())

# Get structured data
validation_dict = result.to_dict()
# {
#   "passed": [...],
#   "warnings": [...],
#   "errors": [...],
#   "success": True/False,
#   "total_checks": N,
#   "passed_count": N,
#   "warning_count": N,
#   "error_count": N,
# }
```

## Testing

```python
from app.services.integration import MCPGenerationPipeline
from app.services.examples import get_example_github_api

def test_complete_pipeline():
    pipeline = MCPGenerationPipeline()
    api = get_example_github_api()
    
    # Generate
    design, files, validation = pipeline.generate_complete_project(api)
    
    # Verify
    assert validation["success"] == True
    assert len(design.tools) > 0
    assert "src/server.py" in files
    assert "requirements.txt" in files
    assert "README.md" in files
    
    # Create ZIP
    zip_buffer = pipeline.create_download_zip(files, design.server_name)
    assert zip_buffer.getbuffer().nbytes > 0
    
    print("✓ All tests passed!")

if __name__ == "__main__":
    test_complete_pipeline()
```

## Common Patterns

### Generate & Validate

```python
design, files, validation = pipeline.generate_complete_project(api)

if validation["success"]:
    print(f"✓ Generated {len(design.tools)} tools")
    zip_buffer = pipeline.create_download_zip(files, design.server_name)
else:
    print("✗ Validation failed:")
    for error in validation["errors"]:
        print(f"  {error}")
```

### Generate with Status Tracking

```python
status = GenerationStatus()

status.update("api_discovery", "completed", "API discovered")
# ... frontend can poll this

status.update("tool_design", "running", "Designing tools...")
design, _, _ = pipeline.generate_complete_project(api)
status.update("tool_design", "completed", f"Designed {len(design.tools)} tools")

status.update("code_generation", "running", "Generating server...")
# ... generation already done
status.update("code_generation", "completed", "Server generated")

status.update("validation", "running", "Validating...")
# ... validation already done
status.update("validation", "completed", "All checks passed")

return status.to_dict()
```

### Store & Retrieve Projects

```python
import json
from pathlib import Path
import uuid

class ProjectStorage:
    def __init__(self, base_path="./projects"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def save_project(self, design, files, api, validation):
        project_id = str(uuid.uuid4())
        project_dir = self.base_path / project_id
        project_dir.mkdir()
        
        # Save metadata
        metadata = {
            "project_id": project_id,
            "server_name": design.server_name,
            "created_at": datetime.now().isoformat(),
            "validation": validation,
        }
        (project_dir / "metadata.json").write_text(json.dumps(metadata))
        
        # Save design
        (project_dir / "design.json").write_text(design.model_dump_json())
        
        # Save API
        (project_dir / "api.json").write_text(api.model_dump_json())
        
        # Save files
        (project_dir / "files").mkdir()
        for filepath, content in files.items():
            file_path = project_dir / "files" / filepath
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
        
        return project_id
    
    def load_project(self, project_id):
        project_dir = self.base_path / project_id
        
        design = MCPServerDesign.model_validate_json(
            (project_dir / "design.json").read_text()
        )
        
        api = APIRepresentation.model_validate_json(
            (project_dir / "api.json").read_text()
        )
        
        files = {}
        files_dir = project_dir / "files"
        for file_path in files_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(files_dir)
                files[str(rel_path)] = file_path.read_text()
        
        return design, api, files

storage = ProjectStorage()
```

### Regenerate with Options

```python
options = {
    "server_name": "my_custom_api",
    "selected_tools": ["get_user", "list_users"],  # Only these
    # other options could include:
    # "include_tests": True,
    # "naming_style": "verbose",
    # "include_destructive": False,
}

design2, files2, val2 = pipeline.regenerate_with_options(
    api=original_api,
    design=original_design,
    options=options
)
```

## Error Handling

```python
from openai import APIError

try:
    design, files, validation = pipeline.generate_complete_project(api)
except APIError as e:
    # OpenAI API error
    return {"error": f"AI generation failed: {str(e)}"}
except ValueError as e:
    # Configuration error
    return {"error": f"Configuration error: {str(e)}"}
except Exception as e:
    # Unexpected error
    return {"error": f"Generation failed: {str(e)}"}
```

## Performance Tips

1. **Cache example APIs** - Use get_example_*() for testing
2. **Reuse pipeline instance** - Don't create new MCPGenerationPipeline per request
3. **Async where possible** - Generator is sync, but can be called from async
4. **Store projects** - Keep generated files for re-download
5. **Progress tracking** - Use GenerationStatus for long operations

## File Sizes

- Typical generated project: 800-1200 lines
- ZIP size: 30-50 KB
- API summary tokens: 2,000-3,000
- AI response tokens: 1,000-2,000
- Total tokens: 3,000-5,000 (~$0.08)

## Useful Constants

```python
# From app/models/mcp.py
TOOL_CATEGORIES = ["read", "write", "admin"]
PARAMETER_TYPES = ["string", "number", "integer", "boolean", "array", "object"]

# From app/config.py
OPENAI_MODEL = "gpt-4-turbo-preview"
REQUEST_TIMEOUT = 20
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB
```

---

For more details, see GENERATOR_GUIDE.md and MCP_GENERATOR_IMPLEMENTATION.md
