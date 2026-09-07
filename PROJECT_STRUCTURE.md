# MCP Server Builder - Project Structure

Professional, organized folder structure for a production-grade AI-powered MCP Server Builder platform.

## Directory Layout

```
mcp-server-builder/
│
├── 📄 Root Configuration Files
│   ├── README.md                          # Main project documentation
│   ├── QUICKSTART.md                      # 5-minute setup guide
│   ├── LICENSE                            # MIT License
│   ├── .env.example                       # Environment variables template
│   ├── .gitignore                         # Git ignore rules
│   ├── pyproject.toml                     # Python project metadata
│   ├── requirements.txt                   # Python dependencies
│   ├── task.md                            # Original task specification
│   └── PROJECT_STRUCTURE.md               # This file
│
├── 📁 docs/                               # Documentation (all guides)
│   ├── ARCHITECTURE.md                    # Technical architecture & design
│   ├── API_REFERENCE.md                   # Complete API endpoints documentation
│   ├── SECURITY.md                        # Security model & threat analysis
│   ├── TESTING.md                         # Testing strategy & coverage
│   ├── DEPLOYMENT.md                      # Production deployment guide
│   ├── CONTRIBUTING.md                    # Contribution guidelines
│   ├── CLAUDE.md                          # Developer context & workflow
│   ├── AGENT.md                           # AI agent instructions
│   │
│   └── generated/                         # Generated documentation
│       ├── FRONTEND_README.md
│       ├── FRONTEND_API_SPECIFICATION.md
│       ├── FRONTEND_BUILD_SUMMARY.md
│       ├── GENERATOR_GUIDE.md
│       ├── GENERATOR_BUILD_COMPLETE.md
│       ├── GENERATOR_IMPLEMENTATION.md
│       ├── INTEGRATION_CHECKLIST.md
│       ├── DELIVERY_VERIFICATION.md
│       ├── QUICK_API_REFERENCE.md
│       └── MCP_GENERATOR_IMPLEMENTATION.md
│
├── 📁 app/                                # Backend FastAPI Application
│   ├── __init__.py
│   ├── __version__.py                     # Version information
│   ├── main.py                            # FastAPI app initialization
│   ├── config.py                          # Configuration & constants
│   │
│   ├── models/                            # Data models (Pydantic)
│   │   ├── __init__.py
│   │   ├── api.py                         # API representation models
│   │   ├── mcp.py                         # MCP tool & server models
│   │   └── project.py                     # Project metadata models
│   │
│   ├── routes/                            # API endpoints
│   │   ├── __init__.py
│   │   ├── pages.py                       # HTML page routes
│   │   ├── analysis.py                    # POST /api/analyze
│   │   ├── generation.py                  # POST /api/design-tools, /api/generate
│   │   ├── projects.py                    # Project CRUD operations
│   │   └── downloads.py                   # GET /api/project/{id}/download
│   │
│   ├── services/                          # Business logic (core functionality)
│   │   ├── __init__.py
│   │   ├── url_fetcher.py                 # SSRF-protected URL fetching
│   │   ├── api_discovery.py               # API detection (OpenAPI, Swagger, REST)
│   │   ├── openapi_parser.py              # OpenAPI/Swagger spec parsing
│   │   ├── api_analyzer.py                # API analysis & filtering
│   │   ├── mcp_designer.py                # AI tool design coordination
│   │   ├── mcp_generator.py               # MCP server code generation
│   │   ├── auto_readme.py                 # Auto-generated README creation
│   │   ├── validator.py                   # Generated server validation
│   │   ├── project_manager.py             # Project file management & ZIP creation
│   │   ├── openai_service.py              # OpenAI GPT-4 mini integration
│   │   ├── integration.py                 # Pipeline orchestration
│   │   └── examples.py                    # Example APIs for testing
│   │
│   └── data/                              # JSON file storage
│       └── (project files stored here)
│
├── 📁 src/                                # Frontend (HTML, CSS, JS)
│   │
│   ├── templates/                         # HTML pages
│   │   ├── index.html                     # Home page (hero, features, CTA)
│   │   ├── builder.html                   # Main builder interface (4-step workflow)
│   │   ├── history.html                   # Project history & management
│   │   ├── project.html                   # Project detail view (4 tabs)
│   │   └── docs.html                      # API documentation page
│   │
│   └── static/                            # Static assets
│       ├── js/                            # JavaScript files
│       │   ├── app.js                     # Core utilities (Toast, API, Validator)
│       │   ├── builder.js                 # Builder workflow (918 lines)
│       │   ├── history.js                 # History management
│       │   └── project.js                 # Project viewer
│       │
│       └── styles/                        # CSS stylesheets
│           └── styles.css                 # Design system & components (1,691 lines)
│
├── 📁 scripts/                            # Utility scripts
│   └── run.py                             # Development server launcher
│
├── 📁 tests/                              # Test suite
│   ├── test_security.py                   # Security tests (SSRF, URL validation)
│   ├── test_discovery.py                  # API discovery tests
│   ├── test_generation.py                 # MCP generation tests
│   └── test_validation.py                 # Validation tests
│
└── 📁 .claude/                            # Claude Code configuration
    └── settings.json                      # Project-specific settings
```

---

## File Organization Principles

### 1. **Root Level** - Only Essential Files
- Configuration (`.env.example`, `pyproject.toml`, `requirements.txt`)
- Documentation metadata (`README.md`, `QUICKSTART.md`, `LICENSE`)
- Version control (`.gitignore`)
- No HTML, JS, or CSS in root

### 2. **docs/** - All Documentation
- **User-facing:** README, QUICKSTART, API_REFERENCE
- **Developer-facing:** CLAUDE.md, CONTRIBUTING, TESTING
- **Operator-facing:** DEPLOYMENT, SECURITY
- **AI-facing:** AGENT.md
- **generated/** subdirectory for agent-generated docs

### 3. **app/** - Backend (FastAPI)
- **main.py** - Single entry point
- **config.py** - Centralized configuration
- **models/** - Data validation (Pydantic)
- **routes/** - HTTP endpoints (REST API)
- **services/** - Business logic (reusable, testable)
- **data/** - Persistent storage (JSON files)

### 4. **src/** - Frontend
- **templates/** - HTML pages (served via Jinja2)
- **static/js/** - JavaScript modules (app, builder, history, project)
- **static/styles/** - Tailwind CSS design system

### 5. **scripts/** - Utilities
- **run.py** - Development server launcher
- Other helper scripts as needed

### 6. **tests/** - Test Suite
- Unit tests for each service
- Integration tests for API routes
- Security tests for SSRF protection

---

## Component Responsibility

### Backend Services (app/services/)

| Service | Responsibility | Lines |
|---------|-----------------|-------|
| `url_fetcher.py` | SSRF-protected HTTP requests | 160 |
| `api_discovery.py` | Find OpenAPI/Swagger specs | 140 |
| `openapi_parser.py` | Parse API specifications | 280 |
| `api_analyzer.py` | Analyze & filter endpoints | 110 |
| `mcp_designer.py` | AI tool design (GPT-4 mini) | 339 |
| `mcp_generator.py` | Generate MCP server code | 462 |
| `auto_readme.py` | Auto-generate README | 369 |
| `validator.py` | Validate generated servers | 321 |
| `project_manager.py` | ZIP creation & file management | 190 |
| `openai_service.py` | OpenAI API integration | 200 |

**Total: 2,571 lines of production code**

### Frontend Assets (src/)

| Asset | Purpose | Lines |
|-------|---------|-------|
| `index.html` | Home page | 321 |
| `builder.html` | Builder interface | 287 |
| `history.html` | History management | 96 |
| `project.html` | Project viewer | 162 |
| `styles.css` | Design system | 1,691 |
| `app.js` | Utilities | 219 |
| `builder.js` | Workflow logic | 918 |
| `history.js` | History logic | 210 |
| `project.js` | Project logic | 385 |

**Total: 4,289 lines of frontend code**

---

## Running the Application

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
cp .env.example .env
# Edit .env and add OPENAI_API_KEY

# Run development server
python scripts/run.py

# Access at http://localhost:8000
```

### Production

```bash
# Use Gunicorn
gunicorn app.main:app --workers 4 --bind 0.0.0.0:8000

# Or use uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Data Flow

```
User enters URL
       ↓
Frontend: src/templates/builder.html
       ↓
API: POST /api/analyze
       ↓
Backend Services:
  1. url_fetcher.py     → Fetch URL safely
  2. api_discovery.py   → Find OpenAPI/Swagger
  3. openapi_parser.py  → Parse specification
  4. api_analyzer.py    → Extract endpoints
       ↓
API: POST /api/design-tools
       ↓
  5. mcp_designer.py    → AI designs tools (GPT-4 mini)
       ↓
API: POST /api/generate
       ↓
  6. mcp_generator.py   → Generate MCP server
  7. auto_readme.py     → Generate README
  8. validator.py       → Validate output
       ↓
API: GET /api/project/{id}/download
       ↓
  9. project_manager.py → Create ZIP file
       ↓
Frontend: Download starts
```

---

## Security Architecture

- **URL Validation:** `url_fetcher.py` - SSRF protection with IP validation
- **Input Validation:** Pydantic models in `models/`
- **API Keys:** Environment variables only, never hardcoded
- **Generated Code:** No secrets in templates
- **Error Handling:** Graceful failures, no stack traces to users

---

## Documentation Structure

### For Users
- `README.md` - What is this?
- `QUICKSTART.md` - How do I start?
- `docs/API_REFERENCE.md` - How do I use the API?

### For Developers
- `docs/ARCHITECTURE.md` - How is it built?
- `docs/CLAUDE.md` - Development workflow
- `docs/TESTING.md` - How do I test?
- `docs/CONTRIBUTING.md` - How do I contribute?

### For Operations
- `docs/DEPLOYMENT.md` - How do I deploy?
- `docs/SECURITY.md` - What are the threats?

### For AI Agents
- `docs/AGENT.md` - Complete system description for Claude

---

## Key Files Reference

### Entry Points
- `app/main.py` - FastAPI application start
- `scripts/run.py` - Development server
- `src/templates/index.html` - Homepage

### Configuration
- `app/config.py` - All constants and settings
- `.env.example` - Environment variables template
- `pyproject.toml` - Project metadata

### Core Logic
- `app/services/` - All business logic
- `app/models/` - Data structures
- `app/routes/` - HTTP endpoints

### Frontend
- `src/templates/` - HTML pages
- `src/static/` - CSS and JavaScript

### Documentation
- `docs/` - All user, developer, operator guides
- `docs/generated/` - Agent-generated documentation

---

## Development Workflow

```
1. Edit code in app/ or src/
2. Update tests in tests/
3. Run `python scripts/run.py` (auto-reload)
4. Test at http://localhost:8000
5. Commit with proper message
6. Push to main branch
```

---

## Deployment Checklist

- [ ] `.env` configured with `OPENAI_API_KEY`
- [ ] `requirements.txt` installed
- [ ] Static files mounted correctly
- [ ] Templates found at correct path
- [ ] Health check passes: `GET /health`
- [ ] Home page loads: `GET /`
- [ ] API responds: `POST /api/analyze` with valid URL

---

**This structure promotes:**
- ✅ Clear separation of concerns
- ✅ Easy navigation for developers
- ✅ Scalability as project grows
- ✅ Professional organization
- ✅ Fast onboarding for new team members
- ✅ Production-ready from day one
