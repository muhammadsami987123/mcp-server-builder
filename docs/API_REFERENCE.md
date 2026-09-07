# API Reference – MCP Server Builder REST API

Complete reference for all MCP Server Builder API endpoints.

## Base URL

```
Development:  http://localhost:8000
Production:   https://api.yourapp.com
```

## Response Format

All endpoints return JSON with consistent format:

```json
{
  "success": true,
  "data": { /* endpoint-specific data */ },
  "error": null,
  "metadata": {
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "0.1.0",
    "request_id": "req_abc123"
  }
}
```

## Endpoints

### 1. Discover API

Discover and parse API documentation at given URL.

```
POST /api/discover
```

**Request**:

```json
{
  "url": "https://api.example.com",
  "follow_links": true,
  "timeout": 20
}
```

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | Yes | HTTPS URL to API documentation |
| `follow_links` | boolean | No | Follow documentation links (default: true) |
| `timeout` | integer | No | Request timeout in seconds (default: 20) |

**Response (Success)**:

```json
{
  "success": true,
  "data": {
    "api": {
      "name": "GitHub API",
      "description": "GitHub REST API",
      "version": "2024-01-01",
      "base_url": "https://api.github.com",
      "source_url": "https://api.github.com",
      "endpoints": [
        {
          "path": "/users/{username}",
          "method": "GET",
          "summary": "Get a user",
          "description": "Get a user by username",
          "parameters": [
            {
              "name": "username",
              "in": "path",
              "required": true,
              "schema": { "type": "string" }
            }
          ],
          "responses": [
            {
              "status_code": "200",
              "description": "User found"
            }
          ]
        }
      ],
      "security_schemes": {
        "bearer": {
          "type": "http",
          "scheme": "bearer"
        }
      },
      "authentication_required": false,
      "authentication_type": null
    },
    "raw_spec": { /* original OpenAPI/Swagger spec */ },
    "detected_type": "openapi3"
  },
  "metadata": { /* ... */ }
}
```

**Response (Error)**:

```json
{
  "success": false,
  "data": null,
  "error": "SSRF blocked: Private IP range detected",
  "metadata": {
    "error_code": "SECURITY_ERROR",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

**Error Codes**:

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Invalid URL format |
| `SECURITY_ERROR` | SSRF block or forbidden URL |
| `TIMEOUT_ERROR` | Request timeout (> 20s) |
| `TOO_LARGE_ERROR` | Response exceeds 10MB |
| `DISCOVERY_ERROR` | Failed to discover API (404, no spec found) |
| `PARSE_ERROR` | Failed to parse API specification |

---

### 2. Analyze API

Analyze discovered API and extract structured endpoint information.

```
POST /api/analyze
```

**Request**:

```json
{
  "discovery_result": {
    "api": { /* from /api/discover response */ },
    "raw_spec": { /* optional */ },
    "detected_type": "openapi3"
  }
}
```

**Response (Success)**:

```json
{
  "success": true,
  "data": {
    "api": {
      "name": "GitHub API",
      "endpoints": [
        {
          "path": "/users/{username}",
          "method": "GET",
          "summary": "Get a user",
          "operation_id": "get_user",
          "tags": ["users"],
          "parameters": [
            {
              "name": "username",
              "in": "path",
              "required": true,
              "description": "The user's username"
            }
          ],
          "responses": [
            {
              "status_code": "200",
              "description": "User found",
              "schema": {
                "type": "object",
                "properties": {
                  "login": { "type": "string" },
                  "id": { "type": "integer" }
                }
              }
            }
          ]
        }
      ],
      "authentication_required": false
    }
  },
  "metadata": { /* ... */ }
}
```

---

### 3. Design Tools (AI)

Generate MCP tool design using AI analysis of API.

```
POST /api/design
```

**Request**:

```json
{
  "api": { /* APIRepresentation from /api/analyze */ },
  "max_tools": 50,
  "tool_categories": ["data_retrieval", "data_modification"]
}
```

**Parameters**:

| Name | Type | Description |
|------|------|-------------|
| `api` | object | APIRepresentation from analyze endpoint |
| `max_tools` | integer | Maximum tools to design (default: 50) |
| `tool_categories` | array | Tool categories to include |

**Response (Success)**:

```json
{
  "success": true,
  "data": {
    "design": {
      "server_name": "github-mcp",
      "server_description": "MCP server for GitHub API",
      "version": "0.1.0",
      "tools": [
        {
          "name": "get_user",
          "description": "Get a GitHub user profile",
          "category": "data_retrieval",
          "api_endpoint": "GET /users/{username}",
          "method": "GET",
          "path": "/users/{username}",
          "parameters": [
            {
              "name": "username",
              "type": "string",
              "description": "GitHub username",
              "required": true
            }
          ],
          "input_schema": {
            "type": "object",
            "properties": {
              "username": {
                "type": "string",
                "description": "GitHub username"
              }
            },
            "required": ["username"]
          },
          "required_auth": null,
          "example_request": {
            "username": "octocat"
          },
          "example_response": {
            "login": "octocat",
            "id": 1,
            "avatar_url": "https://github.com/images/error/octocat_happy.gif"
          }
        }
      ],
      "api_base_url": "https://api.github.com",
      "source_api_name": "GitHub API",
      "authentication_config": null
    }
  },
  "metadata": { /* ... */ }
}
```

---

### 4. Generate Server

Generate complete MCP server code from tool design.

```
POST /api/generate
```

**Request**:

```json
{
  "design": { /* MCPServerDesign from /api/design */ }
}
```

**Response (Success)**:

```json
{
  "success": true,
  "data": {
    "server": {
      "server_name": "github-mcp",
      "main_file": "#!/usr/bin/env python3\n...",
      "tools_file": "...",
      "config_file": "...",
      "requirements_file": "fastapi==0.104.1\n...",
      "readme_file": "# GitHub MCP Server\n...",
      "errors": [],
      "warnings": []
    }
  },
  "metadata": { /* ... */ }
}
```

---

### 5. Validate Server

Validate generated MCP server code.

```
POST /api/validate
```

**Request**:

```json
{
  "server": { /* GeneratedMCPServer from /api/generate */ }
}
```

**Response**:

```json
{
  "success": true,
  "data": {
    "valid": true,
    "errors": [],
    "warnings": [],
    "summary": "Server is valid and ready to use"
  },
  "metadata": { /* ... */ }
}
```

**Validation Checks**:
- Python syntax validity
- Import availability
- MCP schema compliance
- Tool instantiation

---

### 6. Full Generation (Combined)

Generate complete MCP server in one request (discover → design → generate → validate).

```
POST /api/generate-full
```

**Request**:

```json
{
  "url": "https://api.example.com"
}
```

**Response**:

```json
{
  "success": true,
  "data": {
    "project_id": "proj_abc123",
    "server_name": "example-mcp",
    "discovery": { /* DiscoveryResult */ },
    "design": { /* MCPServerDesign */ },
    "generated_server": { /* GeneratedMCPServer */ },
    "validation": { /* ValidationResult */ }
  },
  "metadata": { /* ... */ }
}
```

---

### 7. List Projects

List all generated MCP server projects.

```
GET /api/projects
```

**Query Parameters**:

| Name | Type | Description |
|------|------|-------------|
| `offset` | integer | Pagination offset (default: 0) |
| `limit` | integer | Items per page (default: 20, max: 100) |
| `sort_by` | string | Sort field: `created`, `name` (default: `created`) |
| `sort_order` | string | `asc` or `desc` (default: `desc`) |

**Response**:

```json
{
  "success": true,
  "data": {
    "projects": [
      {
        "project_id": "proj_abc123",
        "name": "GitHub MCP",
        "source_api_name": "GitHub API",
        "created_at": "2024-01-01T12:00:00Z",
        "status": "completed",
        "tool_count": 15
      }
    ],
    "total_count": 1,
    "limit": 20,
    "offset": 0
  },
  "metadata": { /* ... */ }
}
```

---

### 8. Get Project Details

Retrieve complete details for a specific project.

```
GET /api/projects/{project_id}
```

**Path Parameters**:

| Name | Type | Description |
|------|------|-------------|
| `project_id` | string | Unique project identifier |

**Response**:

```json
{
  "success": true,
  "data": {
    "project_id": "proj_abc123",
    "name": "GitHub MCP",
    "description": "MCP server for GitHub API",
    "source_url": "https://api.github.com",
    "source_api_name": "GitHub API",
    "created_at": "2024-01-01T12:00:00Z",
    "status": "completed",
    "tool_count": 15,
    "design": { /* MCPServerDesign */ },
    "generated_files": [
      {
        "path": "main.py",
        "content": "...",
        "file_type": "text"
      }
    ]
  },
  "metadata": { /* ... */ }
}
```

---

### 9. Download Project

Download generated project as ZIP archive.

```
GET /api/projects/{project_id}/download
```

**Response**:

- Content-Type: `application/zip`
- Returns ZIP file containing all project files

**Example**:

```bash
curl -o my-mcp.zip https://localhost:8000/api/projects/proj_abc123/download
unzip my-mcp.zip
```

---

### 10. Delete Project

Delete a generated project and its files.

```
DELETE /api/projects/{project_id}
```

**Response**:

```json
{
  "success": true,
  "data": {
    "message": "Project deleted successfully"
  },
  "metadata": { /* ... */ }
}
```

---

### 11. Health Check

Check API health status.

```
GET /health
```

**Response**:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK – Request succeeded |
| 201 | Created – Resource created |
| 204 | No Content – Delete successful |
| 400 | Bad Request – Invalid parameters |
| 401 | Unauthorized – API key required |
| 403 | Forbidden – SSRF or security violation |
| 404 | Not Found – Resource not found |
| 422 | Unprocessable Entity – Validation error |
| 429 | Too Many Requests – Rate limited |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Error Response Format

```json
{
  "success": false,
  "data": null,
  "error": "Specific error message describing what went wrong",
  "metadata": {
    "error_code": "ERROR_TYPE",
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_abc123"
  }
}
```

### Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `SECURITY_ERROR` | 403 | SSRF block, forbidden URL, or security violation |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests, try again later |
| `SERVER_ERROR` | 500 | Internal server error |
| `TIMEOUT_ERROR` | 408 | Request timeout |
| `DISCOVERY_ERROR` | 422 | Failed to discover API |
| `GENERATION_ERROR` | 500 | Failed to generate server |

---

## Request Examples

### Using cURL

```bash
# Discover API
curl -X POST http://localhost:8000/api/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "https://api.github.com"}'

# Full generation
curl -X POST http://localhost:8000/api/generate-full \
  -H "Content-Type: application/json" \
  -d '{"url": "https://api.github.com"}' \
  -o response.json

# Get projects
curl http://localhost:8000/api/projects

# Download project
curl -o my-mcp.zip \
  http://localhost:8000/api/projects/proj_abc123/download
```

### Using Python

```python
import httpx
import json

async with httpx.AsyncClient() as client:
    # Discover API
    response = await client.post(
        "http://localhost:8000/api/discover",
        json={"url": "https://api.github.com"}
    )
    result = response.json()
    print(result["data"]["api"]["name"])
```

### Using JavaScript

```javascript
// Discover API
const response = await fetch('http://localhost:8000/api/discover', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ url: 'https://api.github.com' })
});

const result = await response.json();
console.log(result.data.api.name);
```

---

## Rate Limiting

Currently: No rate limiting (open API)

Future: Rate limiting will be implemented with:
- Per-IP limits
- Per-API-key limits
- Requests-per-minute threshold

---

## Authentication

Currently: Public API (no authentication required)

Future: API key authentication may be added.

---

## Versioning

Current API version: `0.1.0`

Version changes are announced in CHANGELOG.md.

---

## Support

- **Issues**: https://github.com/marsaempower/mcp-server-builder/issues
- **Discussions**: https://github.com/marsaempower/mcp-server-builder/discussions
- **Security**: security@example.com

---

**Last Updated**: 2024-01-01
