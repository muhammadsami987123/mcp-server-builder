# MCP Server Builder

**Turn any API into a production-ready MCP (Model Context Protocol) server in seconds.**

MCP Server Builder is an AI-powered platform that automatically analyzes API documentation (OpenAPI, Swagger, REST docs) and generates complete, validated, runnable MCP servers. Simply paste a URL, and our AI designs optimal tools, generates tested code, and packages everything for immediate deployment.

## Core Promise

- **Automatic API Analysis** – Discovers OpenAPI specs, Swagger definitions, and REST documentation across any API
- **AI-Driven Tool Design** – GPT-4 intelligently designs optimal MCP tools matched to your API's capabilities
- **Production-Ready Code** – Generated MCP servers include proper error handling, authentication, validation, and logging
- **Complete Package** – Download a fully structured Python project ready to run with `mcp install`
- **Security First** – Built-in SSRF protection, URL validation, and safe API interaction patterns

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-server-builder.git
cd mcp-server-builder

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### Running Locally

```bash
# Start the server with auto-reload
uvicorn app.main:app --reload --port 8000

# Open browser
open http://localhost:8000
```

### Building Your First MCP Server

1. Navigate to http://localhost:8000
2. Paste an API URL (e.g., `https://api.github.com`)
3. Click "Build MCP"
4. Watch as the system:
   - Discovers API endpoints
   - Analyzes parameters and responses
   - Designs MCP tools via AI
   - Generates complete server code
5. Review the generated project and download the ZIP
6. Extract and run: `pip install -r requirements.txt && mcp install`

## Features

### Smart Discovery
- Automatically detects OpenAPI 3.0+ JSON/YAML specs
- Finds Swagger 2.0 definitions
- Extracts data from HTML/Markdown documentation
- Follows documentation links across pages
- Identifies authentication requirements

### AI-Driven Design
- Uses GPT-4 to analyze API capabilities
- Creates logical MCP tool groupings
- Designs tool schemas matching API parameters
- Generates meaningful descriptions and usage examples
- Optimizes for Claude's tool use capabilities

### Automatic Validation
- Validates generated MCP server syntax
- Checks tool schema compatibility
- Verifies authentication configuration
- Tests basic tool instantiation
- Reports detailed validation errors

### Interactive Project Explorer
- Browse generated code in-browser
- Preview file structure and dependencies
- Review tool definitions and implementations
- Export complete project as ZIP

### Project History
- Track all generated MCP servers
- View generation metadata (URL, timestamp, tool count)
- Manage project storage and cleanup

## Architecture Overview

### Frontend
- **Technology**: HTML5, Tailwind CSS, Vanilla JavaScript
- **Purpose**: User interface for URL input, progress tracking, and project browsing
- **Location**: `/index.html`, `/static/`

### Backend
- **Technology**: FastAPI, Uvicorn, Pydantic
- **Purpose**: API orchestration, validation, business logic
- **Key Services**:
  - URL validation and SSRF protection
  - API discovery and documentation parsing
  - MCP tool design via AI
  - Code generation from Jinja2 templates
  - Project storage and retrieval

### AI Integration
- **Model**: OpenAI GPT-4 (via `gpt-4-turbo-preview`)
- **Purpose**: Intelligent MCP tool design based on API analysis
- **Prompting**: Structured prompts for tool naming, descriptions, and categorization

### Data Models
Located in `/app/models/`:
- `api.py` – API discovery (endpoints, parameters, responses, security schemes)
- `mcp.py` – MCP tool definitions and generated server structure
- `project.py` – Project metadata and history tracking

## Project Structure

```
mcp-server-builder/
├── index.html              # Landing page and builder UI
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration, environment, SSRF rules
│   ├── main.py             # FastAPI application and routes
│   ├── services/
│   │   ├── discovery.py    # API discovery and parsing
│   │   ├── analyzer.py     # API analysis and documentation extraction
│   │   ├── designer.py     # MCP tool design via AI
│   │   ├── generator.py    # MCP server code generation
│   │   └── validator.py    # Validation of generated code
│   ├── models/
│   │   ├── api.py          # API representation models
│   │   ├── mcp.py          # MCP server and tool models
│   │   └── project.py      # Project metadata models
│   └── data/               # Local project storage (generated MCPs)
├── templates/              # Jinja2 templates for code generation
├── static/
│   ├── styles.css          # Tailwind CSS
│   └── client.js           # Frontend logic
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── pyproject.toml         # Project metadata and tool config
├── .gitignore             # Git ignore rules
├── LICENSE                # MIT License
├── QUICKSTART.md          # Get started guide
├── ARCHITECTURE.md        # Technical architecture
├── SECURITY.md            # Security documentation
├── TESTING.md             # Testing guide
├── API_REFERENCE.md       # Complete API documentation
├── CONTRIBUTING.md        # Contribution guidelines
└── DEPLOYMENT.md          # Production deployment guide
```

## Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here       # Required: Your OpenAI API key
OPENAI_MODEL=gpt-4-turbo-preview      # AI model for tool design

# Security
REQUEST_TIMEOUT=20                     # HTTP request timeout (seconds)
MAX_RESPONSE_SIZE=10485760            # Max response body size (10MB)
MAX_DISCOVERY_PAGES=10                # Max pages to discover and parse
CORS_ORIGINS=*                        # CORS allowed origins

# Application
DEBUG=false                            # Enable debug mode
LOG_LEVEL=INFO                        # Logging level
```

See `.env.example` for complete configuration.

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | HTML5, Tailwind CSS, Vanilla JS | User interface |
| Backend | FastAPI, Uvicorn | API server and routing |
| Validation | Pydantic | Request/response validation |
| AI | OpenAI GPT-4 | MCP tool design |
| Templates | Jinja2 | Code generation |
| HTTP | httpx | Safe HTTP requests with SSRF protection |
| Config | python-dotenv | Environment configuration |
| Dev Server | Uvicorn | Local development |
| Production | Gunicorn + Uvicorn | Recommended for deployment |

## MCP Generation Pipeline

The system follows this flow to transform an API URL into a complete MCP server:

```
1. URL Validation
   ├─ Format validation (https://)
   ├─ IP whitelisting (blocks private/loopback ranges)
   └─ Redirects follow (max 5 hops)

2. API Discovery
   ├─ Fetch documentation at URL
   ├─ Search for OpenAPI/Swagger specs
   ├─ Find linked documentation
   ├─ Parse HTML/Markdown content
   └─ Extract all API information

3. API Analysis
   ├─ Normalize endpoints (path, method, params)
   ├─ Extract parameter requirements
   ├─ Parse response schemas
   ├─ Identify security schemes
   └─ Detect API patterns and capabilities

4. MCP Design (AI-Driven)
   ├─ Prompt GPT-4 with API analysis
   ├─ Design logical tool groupings
   ├─ Create tool schemas and descriptions
   ├─ Generate example configurations
   └─ Validate design completeness

5. Code Generation
   ├─ Render templates with tool definitions
   ├─ Generate main.py (MCP server)
   ├─ Generate tools.py (tool implementations)
   ├─ Generate config.py (authentication)
   ├─ Create requirements.txt
   └─ Produce README and documentation

6. Validation
   ├─ Check Python syntax
   ├─ Validate MCP schema
   ├─ Verify imports and dependencies
   ├─ Test tool instantiation
   └─ Report errors and warnings

7. Storage & Delivery
   ├─ Save project metadata
   ├─ Store generated files
   ├─ Create project ZIP archive
   └─ Return download link
```

## Security Model

### SSRF Protection
The platform implements multiple layers of protection against Server-Side Request Forgery attacks:

- **IP Blocking**: Rejects requests to private IP ranges (127.x, 10.x, 192.168.x, 172.16-31.x, 224-255.x)
- **Hostname Resolution**: Validates resolved IPs against blocklist
- **Redirect Validation**: Limits redirects to 5 hops, validates each
- **URL Parsing**: Requires explicit `https://` scheme

See `SECURITY.md` for detailed security architecture.

### API Key Management
- **Never commit .env** – API keys stored only in environment variables
- **Runtime loading** – Keys loaded via python-dotenv at startup
- **Proxy pattern** – Generated servers receive keys via environment, never hardcoded
- **Rate limiting ready** – Infrastructure supports API key rate limit tracking

## API Architecture

### Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Landing page |
| `/api/discover` | POST | Discover API documentation at URL |
| `/api/analyze` | POST | Analyze discovered API structure |
| `/api/design` | POST | Design MCP tools via AI |
| `/api/generate` | POST | Generate complete MCP server code |
| `/api/projects` | GET | List all generated projects |
| `/api/projects/{id}` | GET | Retrieve specific project |
| `/api/projects/{id}/download` | GET | Download project as ZIP |

### Request/Response Format

All API requests/responses use JSON with standard structure:

```json
{
  "success": true,
  "data": { /* endpoint-specific data */ },
  "error": null,
  "metadata": {
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "0.1.0"
  }
}
```

See `API_REFERENCE.md` for complete endpoint documentation.

## Testing

Run the complete test suite:

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html

# Run specific test category
pytest tests/test_security.py       # SSRF protection tests
pytest tests/test_discovery.py      # API discovery tests
pytest tests/test_generation.py     # Code generation tests
```

Key test areas:
- **Security**: SSRF protection, URL validation
- **Discovery**: OpenAPI parsing, Swagger extraction, link following
- **Design**: MCP tool creation, schema generation
- **Generation**: Template rendering, syntax validation
- **Integration**: Full pipeline E2E tests

See `TESTING.md` for complete testing guide.

## Limitations & Future Work

### Current Limitations
- **Single API per project** – Each generated server wraps one API
- **HTTP/REST only** – GraphQL and WebSocket APIs need manual adjustment
- **Generic tools** – AI designs tools for all endpoints; production may need customization
- **No auth storage** – Generated servers don't store credentials (by design)
- **Rate limiting** – OpenAI API rate limits affect concurrent generation requests

### Planned Features
- [x] OpenAPI 3.0 and Swagger 2.0 support
- [x] AI-driven tool design
- [ ] GraphQL API support
- [ ] WebSocket/real-time API support
- [ ] Multi-API composition (combine multiple APIs into one MCP server)
- [ ] Tool customization UI
- [ ] CLI for headless generation
- [ ] Automated testing for generated servers
- [ ] Server hosting and one-click deployment
- [ ] Community-contributed server templates
- [ ] Batch generation API

## Contributing

We welcome contributions! See `CONTRIBUTING.md` for guidelines on:
- Setting up development environment
- Code style and standards
- Writing and running tests
- Submitting pull requests
- Commit message format

## Deployment

For production deployment, see `DEPLOYMENT.md` for:
- Environment configuration
- Running with Gunicorn
- Docker containerization
- Monitoring and logging
- Security checklist

Quick production start:

```bash
# Install production dependencies
pip install gunicorn python-dotenv

# Run with Gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## License

This project is licensed under the MIT License. See `LICENSE` for details.

## Support & Issues

- **Bug Reports**: Open an issue on GitHub
- **Feature Requests**: Discuss in GitHub Discussions
- **Security Issues**: Email security@example.com

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) – Modern Python web framework
- [OpenAI API](https://openai.com/api/) – GPT-4 for AI tool design
- [Pydantic](https://docs.pydantic.dev/) – Data validation
- [Tailwind CSS](https://tailwindcss.com/) – Styling framework
