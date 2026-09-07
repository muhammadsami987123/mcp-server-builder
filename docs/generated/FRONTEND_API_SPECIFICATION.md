# Frontend API Specification

This document describes all API endpoints the frontend expects from the FastAPI backend.

## Base URL
```
http://localhost:8000
```

## Page Routes (Server-Rendered HTML)

### GET /
Home page with hero, features, FAQ, etc.

### GET /builder
Main builder interface

### GET /history
History of generated MCP servers

### GET /project/{project_id}
View a specific generated project

---

## API Endpoints

All API endpoints are called from JavaScript via `fetch()`.

### Analysis & Discovery

#### POST /api/analyze
Analyzes a URL and discovers API information.

**Request:**
```json
{
    "url": "https://api.example.com/docs",
    "use_demo": false
}
```

**Response:**
```json
{
    "api_name": "Example API",
    "description": "Example API Description",
    "base_url": "https://api.example.com",
    "endpoints": [
        {
            "path": "/users",
            "method": "GET",
            "description": "List all users",
            "parameters": [],
            "operation_id": "list_users"
        },
        {
            "path": "/users/{id}",
            "method": "GET",
            "description": "Get a specific user",
            "parameters": [
                {
                    "name": "id",
                    "type": "string",
                    "required": true,
                    "description": "User ID"
                }
            ],
            "operation_id": "get_user"
        }
    ],
    "authentication": {
        "type": "bearer",
        "description": "Bearer token required",
        "header": "Authorization"
    },
    "schemas": [
        {
            "name": "User",
            "type": "object",
            "properties": {
                "id": { "type": "string" },
                "name": { "type": "string" },
                "email": { "type": "string" }
            }
        }
    ]
}
```

**Error Response:**
```json
{
    "detail": "Could not reach URL: Connection timeout"
}
```

---

### MCP Tool Generation

#### POST /api/design-tools
Uses AI to design optimal MCP tools from discovered API endpoints.

**Request:**
```json
{
    "api_info": {
        "name": "Example API",
        "description": "...",
        "endpoints": [...]
    },
    "preferences": {
        "tool_naming_style": "snake_case",
        "include_read_only": true,
        "include_destructive": true,
        "group_by_resource": true
    }
}
```

**Response:**
```json
{
    "tools": [
        {
            "name": "list_users",
            "description": "List all users from the Example API",
            "method": "GET",
            "path": "/users",
            "operation_id": "list_users",
            "input_schema": {
                "type": "object",
                "properties": {
                    "limit": { "type": "integer", "description": "Max results" },
                    "offset": { "type": "integer", "description": "Offset" }
                },
                "required": []
            },
            "output_schema": {
                "type": "array",
                "items": { "type": "object" }
            }
        }
    ],
    "server_name": "example_api_mcp",
    "server_description": "MCP server for Example API"
}
```

---

### MCP Server Generation

#### POST /api/generate
Generates the complete MCP server project.

**Request:**
```json
{
    "api_info": {...},
    "designed_tools": [...],
    "project_name": "example_api_mcp",
    "selected_tool_ids": ["list_users", "get_user"],
    "options": {
        "include_tests": true,
        "include_readme": true,
        "include_env_example": true
    }
}
```

**Response:**
```json
{
    "project_id": "project_1234567890",
    "name": "example_api_mcp",
    "description": "MCP server for Example API",
    "files": [
        {
            "path": "src/server.py",
            "name": "server.py",
            "type": "python",
            "size": 2500
        },
        {
            "path": "src/client.py",
            "name": "client.py",
            "type": "python",
            "size": 1800
        },
        {
            "path": "requirements.txt",
            "name": "requirements.txt",
            "type": "text",
            "size": 450
        },
        {
            "path": "README.md",
            "name": "README.md",
            "type": "markdown",
            "size": 3200
        }
    ],
    "file_contents": {
        "src/server.py": "#!/usr/bin/env python3\n...",
        "src/client.py": "...",
        "requirements.txt": "mcp>=0.1.0\n...",
        "README.md": "# Example API MCP\n..."
    }
}
```

---

### Validation

#### POST /api/validate
Validates the generated MCP server.

**Request:**
```json
{
    "project_id": "project_1234567890",
    "files": {...}
}
```

**Response:**
```json
{
    "valid": true,
    "checks_passed": 12,
    "warnings": 0,
    "errors": 0,
    "items": [
        {
            "type": "success",
            "title": "Project structure",
            "message": "All required files present"
        },
        {
            "type": "success",
            "title": "Python syntax",
            "message": "All Python files have valid syntax"
        }
    ]
}
```

---

### Downloads

#### GET /api/project/{project_id}/download
Downloads the complete generated project as a ZIP file.

**Response:**
- Content-Type: `application/zip`
- Content-Disposition: `attachment; filename="mcp-server.zip"`
- Binary ZIP file content

---

### Project Information

#### GET /api/project/{project_id}
Gets details about a specific generated project.

**Response:**
```json
{
    "id": "project_1234567890",
    "name": "example_api_mcp",
    "description": "MCP server for Example API",
    "created_at": "2024-09-07T15:30:00Z",
    "api_url": "https://api.example.com/docs",
    "tools_count": 5,
    "files": [...],
    "validation": {...},
    "readme": "..."
}
```

---

## Error Handling

All error responses follow this format:

```json
{
    "detail": "Error message describing what went wrong"
}
```

HTTP Status Codes:
- `200` - Success
- `400` - Bad Request (invalid input)
- `408` - Timeout (request took too long)
- `422` - Validation Error (invalid URL, malformed data)
- `500` - Internal Server Error

Example error:
```json
{
    "detail": "Invalid URL: Must be HTTPS"
}
```

---

## Frontend State Management

### localStorage Keys
- `mcpHistory` - Array of previously generated projects
  ```json
  [
      {
          "id": "project_1234567890",
          "name": "example_api_mcp",
          "url": "https://api.example.com/docs",
          "tools": 5,
          "timestamp": "2024-09-07T15:30:00Z",
          "project": {...}
      }
  ]
  ```

### sessionStorage Keys
- `initialUrl` - URL passed from home to builder
- `useDemo` - Flag to use demo data
- `currentProjectId` - ID of project being viewed
- `currentProject` - Project data being viewed

---

## Streaming Progress (Optional Enhancement)

For better UX during long operations, consider implementing Server-Sent Events (SSE):

```
GET /api/analyze/progress?request_id=req_123
```

Returns stream of events:
```
data: {"stage": "connect", "status": "completed"}
data: {"stage": "inspect", "status": "running"}
data: {"stage": "detect", "status": "waiting"}
```

Frontend would:
1. Start analysis with: `POST /api/analyze`
2. Receive: `{"request_id": "req_123"}`
3. Connect to SSE stream
4. Update progress in real-time

---

## Security Notes

1. **SSRF Protection**: Backend must validate URLs:
   - Block `localhost`, `127.0.0.1`, `0.0.0.0`
   - Block private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
   - Block link-local addresses (169.254.0.0/16)
   - Block internal hostnames (metadata.google.internal, etc.)
   - Require HTTPS for external URLs
   - Timeout requests after 20 seconds
   - Limit response size to 10MB

2. **API Key Security**:
   - Never expose API keys in frontend code
   - Never log API keys
   - Use environment variables on backend
   - Generated projects should use environment variables

3. **Input Validation**:
   - Validate all user inputs
   - Sanitize file paths
   - Validate JSON schemas
   - Prevent path traversal

---

## Frontend-to-Backend Communication Flow

### Analysis Flow
```
User enters URL
    ↓
Frontend validates URL
    ↓
POST /api/analyze
    ↓
Backend discovers API
    ↓
Backend returns endpoints
    ↓
Frontend displays tool selection
```

### Generation Flow
```
User selects tools
    ↓
POST /api/design-tools (optional AI design)
    ↓
Backend returns designed tools
    ↓
POST /api/generate
    ↓
Backend generates MCP server
    ↓
POST /api/validate
    ↓
Backend validates
    ↓
Frontend displays result
    ↓
GET /api/project/{id}/download
    ↓
User downloads ZIP
```

---

## Implementation Checklist for Backend

- [ ] GET / - Home page
- [ ] GET /builder - Builder page
- [ ] GET /history - History page
- [ ] GET /project/{id} - Project detail page
- [ ] POST /api/analyze - URL analysis
- [ ] POST /api/design-tools - AI tool design
- [ ] POST /api/generate - Project generation
- [ ] POST /api/validate - Project validation
- [ ] GET /api/project/{id} - Get project info
- [ ] GET /api/project/{id}/download - Download ZIP
- [ ] SSRF protection implemented
- [ ] Error handling and logging
- [ ] Rate limiting
- [ ] Security headers
- [ ] CORS configuration (if needed)

---

## Testing the Frontend

The frontend is fully functional with demo mode:

1. Navigate to `/builder`
2. Click "Try Demo" button
3. Follow through the complete workflow

The frontend will:
- Show realistic progress stages
- Simulate API analysis
- Display mock tools
- Generate demo project
- Allow downloading (creates empty ZIP)
- Save to history

No backend API required for initial testing/development!
