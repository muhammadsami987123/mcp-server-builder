# Build a Complete AI MCP Server Builder

You are a senior full-stack engineer, AI engineer, product architect, and UI/UX designer.

Build a **complete, production-quality AI MCP Server Builder** from scratch.

This is **NOT an MVP**.

This is **NOT a generic API tool builder**.

This is specifically a platform that allows a user to enter a **URL**, automatically understand the API/documentation behind that URL, and generate a complete, runnable **MCP server** from it.

The core experience is:

**Enter URL → Analyze → Understand API → Design MCP Tools → Generate MCP Server → Validate → Inspect → Download → Run**

The final application must feel like a serious developer product, not a student project or a basic CRUD dashboard.

---

# 1. Core Product Concept

The user should be able to enter something like:

```text
https://example.com/docs
```

or:

```text
https://api.example.com
```

or a URL containing:

* OpenAPI documentation
* Swagger documentation
* REST API documentation
* API reference
* developer documentation
* endpoint documentation
* machine-readable API specifications

The system then:

1. Validates the URL.
2. Safely fetches the URL.
3. Detects what kind of documentation/API exists.
4. Discovers linked documentation pages where appropriate.
5. Detects OpenAPI/Swagger specifications.
6. Parses endpoints.
7. Extracts HTTP methods.
8. Extracts parameters.
9. Extracts request bodies.
10. Extracts response schemas.
11. Extracts authentication requirements.
12. Understands endpoint descriptions.
13. Groups related endpoints.
14. Determines useful MCP tools.
15. Uses OpenAI GPT-4.1-mini to intelligently design the MCP interface.
16. Generates a complete MCP server.
17. Validates the generated server.
18. Shows the generated project in an interactive code/project explorer.
19. Allows the user to download the complete project.
20. Provides instructions for running the MCP server.

The generated output must be an **actual MCP server**, not merely code that calls APIs.

---

# 2. Required Technology Stack

Use exactly this architecture unless there is a very strong technical reason otherwise.

## Frontend

* HTML
* Tailwind CSS
* Vanilla JavaScript

Do NOT use:

* React
* Next.js
* Vue
* Angular
* Svelte
* frontend Node.js frameworks

## Backend

* Python
* FastAPI
* Uvicorn
* Pydantic
* Jinja2

## AI

Use:

* OpenAI API
* GPT-4.1-mini

Use the official OpenAI Python SDK.

## Storage

Do not introduce PostgreSQL, MongoDB, Redis, or unnecessary infrastructure.

Use:

* local JSON files for server-side project/history data where necessary
* localStorage for appropriate browser-side state

The application must run locally with:

```bash
uvicorn app.main:app --reload --port 8000
```

---

# 3. FIRST STEP: Inspect Existing Styles

Before implementing the UI:

Inspect the existing project files and especially the existing styles file.

Do NOT blindly replace the existing styling system.

Identify:

* CSS variables
* spacing system
* typography
* buttons
* cards
* inputs
* forms
* modals
* navigation
* responsive behavior
* animations
* utility classes
* existing visual language

Reuse compatible styles wherever possible.

Improve them where necessary.

The final UI must feel like one coherent premium product.

---

# 4. Product Positioning

The product should communicate one extremely clear promise:

> Give me an API or documentation URL, and I will understand it and build a usable MCP server for you.

Do not make the interface feel like:

* Swagger UI
* Postman
* an API documentation viewer
* a generic AI code generator
* a generic dashboard
* a generic workflow builder

The central product identity is:

**AI-powered MCP Server Generation.**

---

# 5. UI / UX DIRECTION

Create the UI yourself.

There is no external UI reference.

Design a premium 2026 developer SaaS product.

Use a:

* light theme
* sophisticated white/off-white base
* subtle neutral surfaces
* refined borders
* strong typography
* restrained accent colors
* subtle shadows
* clean code-editor surfaces
* excellent spacing
* professional developer-product aesthetics

Avoid:

* excessive gradients
* excessive glassmorphism
* giant rounded cards everywhere
* childish illustrations
* excessive animations
* dark-only UI
* generic AI-dashboard aesthetics
* excessive purple/pink AI branding

The interface should feel closer to a serious developer platform than a template.

Everything must be responsive.

Desktop, tablet, and mobile must all work properly.

---

# 6. Application Pages

Build all pages necessary for a complete product.

At minimum:

## Public Pages

### Home

Sections:

* Navbar
* Hero
* URL input
* Product explanation
* How it works
* Example MCP generation
* Supported API/documentation formats
* MCP explanation
* Generated server preview
* Features
* Security section
* Developer workflow
* FAQ
* CTA
* Footer

The hero should immediately focus on the URL input.

Example:

```text
Turn Any API Into an MCP Server

Paste your API or documentation URL.
Our AI analyzes it, designs the MCP interface, and generates a complete runnable MCP server.

[ https://your-api.com/docs                     ]
                                      [ Build MCP ]
```

Do not clutter the hero.

---

# 7. Main Builder Experience

Create a dedicated builder interface.

Possible route:

```text
/builder
```

The builder should be the core application.

Structure it professionally.

Include:

* URL input
* analysis status
* discovered API information
* endpoint explorer
* MCP tool designer
* generated server
* validation
* project explorer

Do not put everything into one giant page.

Create a clear progressive workflow.

---

# 8. URL INPUT

The user should only need to start with a URL.

Support:

```text
https://example.com/docs
https://api.example.com
https://example.com/openapi.json
https://example.com/swagger.json
```

Provide:

* URL validation
* HTTPS preference
* clear error states
* loading state
* recent URLs
* example URL

The user should not need to manually upload an OpenAPI file unless you choose to support it as an optional advanced feature.

The primary flow MUST remain:

**URL only.**

---

# 9. ANALYSIS EXPERIENCE

When the user clicks:

**Build MCP**

do not simply show:

```text
Loading...
```

Create a professional analysis experience.

Show real stages such as:

```text
Connecting to URL
✓

Inspecting documentation
✓

Detecting API specification
✓

Parsing endpoints
●

Understanding authentication
○

Designing MCP tools
○

Generating server
○

Validating implementation
○
```

Each stage should update based on actual backend progress.

Do not fake completion states.

The UI should clearly distinguish:

* completed
* running
* waiting
* failed

---

# 10. API DISCOVERY ENGINE

Implement a real backend discovery pipeline.

The backend should inspect the supplied URL and attempt to discover:

### OpenAPI

Common locations:

```text
/openapi.json
/openapi.yaml
/swagger.json
/swagger.yaml
/api-docs
/docs
```

Also inspect HTML/documentation links where appropriate.

### Swagger

Detect Swagger UI and associated specification files.

### REST documentation

Parse accessible API documentation pages.

### Machine-readable schemas

Support JSON/YAML API specifications where possible.

Do not assume that every URL contains an API.

If the URL cannot be interpreted as an API/documentation source, explain why.

---

# 11. SECURITY

This application fetches arbitrary URLs.

Treat this as a serious security boundary.

Implement SSRF protections.

At minimum:

* HTTPS preferred
* request timeout
* redirect validation
* block localhost
* block loopback addresses
* block private IP ranges
* block link-local addresses
* block internal hostnames
* validate resolved addresses
* limit response size
* limit number of fetched pages
* prevent recursive crawling
* restrict content types
* protect against infinite redirects
* sanitize parsed HTML
* never execute downloaded JavaScript
* never execute arbitrary code from the target website

Never allow a user-supplied URL to make unrestricted internal network requests.

---

# 12. API UNDERSTANDING ENGINE

Create a structured internal representation of the discovered API.

Represent things such as:

```text
API
├── name
├── description
├── base_url
├── authentication
├── servers
├── endpoints
│   ├── path
│   ├── method
│   ├── operation_id
│   ├── summary
│   ├── description
│   ├── parameters
│   ├── request_body
│   ├── responses
│   └── schemas
└── metadata
```

Do not send huge raw documentation directly to OpenAI.

First normalize and structure the discovered API.

---

# 13. AUTHENTICATION DETECTION

Detect authentication requirements where possible.

Support patterns such as:

* API key
* Bearer token
* OAuth-style configuration
* Basic authentication
* custom headers

The system must clearly tell the user what was detected.

Example:

```text
Authentication

Bearer Token detected

Required header:
Authorization: Bearer <token>
```

Do not expose actual secret credentials.

Never store user API keys or tokens in generated frontend code.

Generated projects should use environment variables.

Example:

```env
API_BASE_URL=
API_KEY=
API_TOKEN=
```

---

# 14. AI MCP TOOL DESIGNER

This is one of the most important parts.

OpenAI GPT-4.1-mini should analyze the normalized API representation.

The AI should determine:

* which endpoints should become MCP tools
* useful tool names
* descriptions
* input schemas
* required parameters
* optional parameters
* tool grouping
* sensible naming
* safe defaults
* dependencies between operations

Example API:

```text
GET /users
GET /users/{id}
POST /users
DELETE /users/{id}
```

The AI might design:

```text
list_users
get_user
create_user
delete_user
```

The generated MCP tools must have clean developer-friendly interfaces.

Do not blindly expose every raw HTTP endpoint if that creates a poor MCP interface.

---

# 15. AI OUTPUT CONTRACT

The AI must return strict structured JSON.

Example:

```json
{
  "server_name": "example_api_mcp",
  "description": "MCP server for Example API",
  "tools": [
    {
      "name": "list_users",
      "description": "List users from the Example API",
      "method": "GET",
      "path": "/users",
      "input_schema": {},
      "parameters": []
    }
  ]
}
```

Use Pydantic models to validate the AI response.

If the response fails validation:

1. attempt structured correction
2. retry if appropriate
3. never blindly trust malformed AI output

---

# 16. MCP SERVER GENERATION

Generate a real MCP server project.

The generated server must contain actual MCP tool definitions.

Use a current, maintained Python MCP implementation compatible with the project requirements.

The generated server should:

* initialize an MCP server
* register tools
* define input schemas
* call the discovered API
* handle authentication
* validate inputs
* handle HTTP errors
* return useful structured results
* handle timeouts
* handle API failures
* expose clear tool descriptions

The MCP implementation must be runnable.

---

# 17. GENERATED PROJECT STRUCTURE

Generate a clean project.

For example:

```text
generated-mcp-server/
│
├── src/
│   ├── server.py
│   ├── config.py
│   ├── client.py
│   ├── models.py
│   │
│   └── tools/
│       ├── __init__.py
│       ├── users.py
│       ├── products.py
│       └── ...
│
├── tests/
│   ├── test_client.py
│   ├── test_tools.py
│   └── ...
│
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── mcp-config.json
└── pyproject.toml
```

Adapt the structure depending on the discovered API.

Do not create unnecessary files.

---

# 18. GENERATED CODE QUALITY

The generated code must be:

* readable
* modular
* typed
* documented
* maintainable
* secure
* logically organized

Avoid generating one enormous `server.py`.

Separate tools into logical modules.

Use shared API client logic.

Use centralized configuration.

Use environment variables for secrets.

Do not hardcode credentials.

---

# 19. MCP TOOL EXPLORER

After generation, create an interactive tool explorer.

Show every generated MCP tool.

Example:

```text
MCP Tools

list_users
GET /users

Get all users from the API.

Input
No parameters

Output
User[]
```

Another:

```text
get_user

GET /users/{id}

Input

id
string
required
```

Allow users to inspect:

* name
* description
* HTTP mapping
* input schema
* required parameters
* output behavior
* source endpoint

---

# 20. GENERATED PROJECT EXPLORER

Create a VS Code-inspired but original project explorer.

Left side:

```text
generated-mcp-server
  src
    tools
      users.py
      products.py
    client.py
    config.py
    server.py
  tests
  README.md
  requirements.txt
```

Center:

code viewer/editor-style interface.

Right side:

metadata/details.

Features:

* file tree
* syntax highlighting
* copy file
* copy project
* download
* search files
* expand/collapse folders

The code viewer can be read-only.

---

# 21. VALIDATION ENGINE

Do not tell the user the MCP server is valid simply because code was generated.

Perform real validation.

Check:

* generated files exist
* Python syntax
* imports
* required configuration
* tool definitions
* Pydantic schemas
* endpoint references
* environment variables
* MCP server initialization
* generated project consistency

Where safely possible, perform static compilation/import checks.

Never execute arbitrary generated code from untrusted sources without isolation.

---

# 22. VALIDATION UI

Show a professional validation report.

Example:

```text
Server Validation

✓ Project structure
✓ Python syntax
✓ MCP server initialization
✓ Tool schemas
✓ API client
✓ Environment configuration
✓ README
✓ Requirements

12 checks passed
0 warnings
0 errors
```

If there are warnings:

```text
⚠ OAuth configuration requires manual credentials
⚠ Endpoint response schema could not be determined
```

Be honest.

---

# 23. README GENERATION

Generate a high-quality README automatically.

It should include:

* project description
* requirements
* installation
* environment variables
* configuration
* running instructions
* available MCP tools
* authentication setup
* MCP client configuration
* examples
* troubleshooting

Example:

```bash
pip install -r requirements.txt
```

and:

```bash
python src/server.py
```

Use the actual generated architecture rather than generic instructions.

---

# 24. MCP CLIENT CONFIGURATION

Generate a configuration example for common MCP client usage where appropriate.

Do not invent unsupported configuration formats.

Clearly label examples.

For example:

```json
{
  "mcpServers": {
    "example-api": {
      "command": "python",
      "args": ["src/server.py"]
    }
  }
}
```

Adapt this to the actual generated server.

---

# 25. DOWNLOAD SYSTEM

The user must be able to download the complete generated MCP server as a ZIP.

The ZIP must contain the actual generated project files.

Also allow:

* download individual file
* copy file
* copy all code

Do not create fake download buttons.

---

# 26. MCP SERVER RESULT PAGE

Create a polished final result page.

Show:

```text
MCP Server Ready

Example API MCP

14 tools generated
14 tools validated
0 errors

[ Download Server ]
[ View Tools ]
[ View Code ]
[ README ]
```

Also show:

* server name
* description
* tool count
* validation status
* authentication status
* generated timestamp

---

# 27. DISCOVERY REPORT

Create a complete API discovery report.

Include:

### API Overview

* name
* description
* base URL

### Authentication

* type
* required credentials
* configuration

### Endpoints

* total endpoint count
* methods
* endpoint groups

### Schemas

* discovered schemas
* request models
* response models

### MCP Design

* generated tools
* ignored endpoints
* grouped endpoints
* reasoning/explanation where useful

Do not expose hidden chain-of-thought.

Provide concise design rationale, not internal reasoning.

---

# 28. SEARCH AND FILTERING

For large APIs, users must be able to search:

* endpoints
* MCP tools
* files
* schemas

Filters:

```text
GET
POST
PUT
PATCH
DELETE
```

and categories/groups.

---

# 29. PROJECT HISTORY

Implement project history.

The user should see previous generated projects.

Example:

```text
Recent MCP Servers

GitHub API MCP
18 tools
2 hours ago

Stripe API MCP
24 tools
Yesterday

Weather API MCP
7 tools
3 days ago
```

Use local JSON storage.

No authentication system is required.

---

# 30. REGENERATE / CUSTOMIZE

After the MCP server is generated, allow the user to modify generation preferences.

Examples:

```text
Server name
Description
Tool naming style
Include read-only endpoints
Include destructive endpoints
Group tools by resource
Generate tests
Generate documentation
```

Then regenerate the affected project.

Do not require starting over.

---

# 31. TOOL SELECTION

Allow users to review generated tools before final generation.

Example:

```text
Select MCP Tools

✓ list_users
✓ get_user
✓ create_user
□ delete_user

[ Generate Server ]
```

This gives the user control over what becomes an MCP tool.

---

# 32. DESTRUCTIVE OPERATIONS

Clearly identify dangerous operations.

Examples:

```text
DELETE /users/{id}
```

should appear as:

```text
⚠ Destructive operation
```

Never silently hide destructive endpoints.

Allow users to exclude them.

---

# 33. AI SAFETY / ACCURACY RULES

The AI must never hallucinate:

* endpoints
* parameters
* authentication
* schemas
* API capabilities

Every generated MCP tool must map back to a discovered API endpoint.

Maintain source metadata internally:

```text
MCP Tool
→ HTTP method
→ endpoint
→ source documentation
```

If information cannot be verified, mark it as unknown.

Do not fabricate.

---

# 34. API RESPONSE HANDLING

Generated MCP tools should handle:

* JSON
* text
* empty responses
* HTTP errors
* validation errors
* authentication errors
* rate limits
* timeouts

Return useful MCP-compatible results.

Do not dump raw stack traces to users.

---

# 35. ERROR UX

Create excellent error handling.

Examples:

### Invalid URL

```text
This URL is not valid.
Check the address and try again.
```

### API unavailable

```text
We couldn't reach this API.

The server returned:
503 Service Unavailable
```

### No API detected

```text
We reached the website, but couldn't identify a usable API or API specification.
```

### Authentication required

```text
This API requires authentication before its documentation can be fully analyzed.
```

Explain what the user can do next.

---

# 36. LOADING STATES

Every asynchronous operation needs a proper state.

Implement:

* skeleton loaders
* progress indicators
* animated processing states
* disabled buttons while processing
* success states
* error states
* retry states

Never leave users staring at an empty page.

---

# 37. TOAST SYSTEM

Create a consistent toast notification system for:

* copied
* downloaded
* generated
* saved
* validation complete
* error
* regenerated

---

# 38. RESPONSIVE DESIGN

Desktop should provide the full developer workspace.

Tablet should intelligently collapse panels.

Mobile should transform:

```text
Sidebar
Code panel
Details panel
```

into accessible stacked views.

Do not simply shrink the desktop layout.

Actually design the mobile experience.

---

# 39. ACCESSIBILITY

Implement:

* semantic HTML
* keyboard navigation
* visible focus states
* ARIA labels where required
* sufficient contrast
* accessible forms
* accessible dialogs
* accessible navigation

---

# 40. SEO

For the public website:

* title
* meta description
* Open Graph metadata
* semantic headings
* canonical URL
* robots.txt
* sitemap.xml
* structured metadata where appropriate

The builder itself can be application-style.

---

# 41. API ROUTES

Create clean FastAPI routes.

For example:

```text
GET  /
GET  /builder
GET  /history
GET  /project/{id}

POST /api/analyze
POST /api/discover
POST /api/design-tools
POST /api/generate
POST /api/validate
POST /api/regenerate

GET  /api/project/{id}
GET  /api/project/{id}/files
GET  /api/project/{id}/download
GET  /api/project/{id}/tools

POST /api/project/{id}/feedback
```

Adapt as necessary.

---

# 42. BACKEND ARCHITECTURE

Keep the backend modular.

Example:

```text
app/
├── main.py
├── config.py
├── models/
│   ├── api.py
│   ├── mcp.py
│   └── project.py
│
├── routes/
│   ├── pages.py
│   ├── analysis.py
│   ├── generation.py
│   ├── projects.py
│   └── downloads.py
│
├── services/
│   ├── url_fetcher.py
│   ├── api_discovery.py
│   ├── openapi_parser.py
│   ├── documentation_parser.py
│   ├── api_analyzer.py
│   ├── mcp_designer.py
│   ├── mcp_generator.py
│   ├── validator.py
│   ├── project_store.py
│   └── openai_service.py
│
├── templates/
│
├── static/
│   ├── js/
│   └── ...
│
└── data/
```

Keep responsibilities separated.

---

# 43. OPENAI SERVICE

Centralize OpenAI interactions.

Do not scatter OpenAI calls across route handlers.

Create something similar to:

```text
openai_service.py
```

Responsibilities:

* MCP tool design
* optional API interpretation
* regeneration
* structured output validation
* retry handling
* token-efficient prompts

Use GPT-4.1-mini.

Never expose the API key to the frontend.

---

# 44. TOKEN EFFICIENCY

Do not send entire websites blindly to the model.

Pipeline:

```text
URL
↓
Fetch
↓
Extract
↓
Normalize
↓
Parse
↓
Compress relevant API information
↓
OpenAI
↓
MCP tool design
```

Only send the model information it actually needs.

For large APIs:

* summarize documentation
* chunk endpoint groups
* normalize schemas
* avoid duplicate descriptions

---

# 45. CACHING

Avoid unnecessary repeated requests.

Cache appropriate discovery results during the current generation process.

Do not build Redis.

Simple local caching is sufficient.

---

# 46. DEMO MODE

Include a real demo mode using a local example API specification.

This is useful when:

* internet access fails
* users want to understand the product
* development/testing is being performed

The demo must use realistic data and follow the exact same generation pipeline.

Do not fake the final generated project.

---

# 47. TESTING

Create tests for:

### URL security

* localhost blocked
* private IP blocked
* invalid URLs
* redirects
* timeout
* oversized responses

### Discovery

* OpenAPI JSON
* OpenAPI YAML
* Swagger
* documentation pages

### AI output

* valid schema
* invalid schema
* missing fields
* malformed response

### MCP generation

* generated files
* tool registration
* configuration
* README
* requirements

### Validation

* syntax validation
* project consistency

---

# 48. COMPLETE USER JOURNEY

You must test the complete flow:

```text
Home
↓
Enter URL
↓
Click Build MCP
↓
URL validation
↓
API discovery
↓
Documentation analysis
↓
Endpoint extraction
↓
Authentication detection
↓
AI MCP tool design
↓
Tool review
↓
Generate MCP Server
↓
Validation
↓
MCP Server Ready
↓
Inspect tools
↓
Inspect project
↓
Inspect code
↓
Download ZIP
↓
Read README
```

Every step must actually work.

---

# 49. NO FAKE FUNCTIONALITY

This is extremely important.

Do NOT create buttons that only visually work.

If there is:

```text
Generate
```

it must actually generate.

If there is:

```text
Download
```

it must generate a real ZIP.

If there is:

```text
Validate
```

it must perform validation.

If there is:

```text
Analyze
```

it must actually analyze the URL.

If there is:

```text
Copy
```

it must copy.

If there is:

```text
Search
```

it must search.

If there is:

```text
Regenerate
```

it must regenerate.

---

# 50. ENVIRONMENT VARIABLES

Create:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
REQUEST_TIMEOUT=20
MAX_RESPONSE_SIZE=
MAX_DISCOVERY_PAGES=
```

Never commit secrets.

Create `.gitignore`.

---

# 51. README FOR THE MAIN APPLICATION

Create a professional README explaining:

* what the product does
* architecture
* installation
* environment variables
* running locally
* project structure
* API architecture
* MCP generation flow
* security model
* testing
* limitations

---

# 52. VISUAL POLISH

Spend significant effort on UI details.

Implement:

* excellent typography
* proper spacing rhythm
* hover states
* focus states
* subtle transitions
* polished code blocks
* elegant empty states
* skeleton loaders
* clear hierarchy
* responsive navigation
* polished modals
* consistent icons
* professional tables
* endpoint badges
* tool status indicators
* validation indicators

The result should look like a real developer SaaS product that could be publicly launched.

---

# 53. IMPORTANT PRODUCT PRINCIPLE

Do not overcomplicate the first interaction.

The first screen should communicate:

```text
Paste a URL.
We'll build the MCP server.
```

Everything else should progressively appear as the system analyzes the API.

The user should never need to understand MCP internals before starting.

The product should do the hard work.

---

# 54. FINAL IMPLEMENTATION STANDARD

Build the application completely.

Do not stop after creating:

* homepage
* static dashboard
* fake analysis
* mock API cards
* placeholder code
* fake MCP tools

The actual pipeline must work.

The finished system must be capable of:

**URL → API Discovery → API Understanding → MCP Tool Design → MCP Server Generation → Validation → Project Download**

with real FastAPI backend logic, real OpenAI GPT-4.1-mini usage, real generated files, and a polished frontend.

Before finishing:

1. Inspect every page.
2. Test every navigation path.
3. Test every major button.
4. Test URL validation.
5. Test SSRF protection.
6. Test OpenAPI parsing.
7. Test AI tool generation.
8. Test MCP generation.
9. Test validation.
10. Test ZIP download.
11. Test responsive layouts.
12. Fix all console errors.
13. Fix all broken API routes.
14. Remove placeholder content.
15. Remove fake interactions.
16. Ensure generated MCP servers are internally consistent.
17. Ensure the UI is polished without requiring manual redesign.

Do not ask me to design the UI for you.

Make strong professional product decisions yourself.

The final result should feel like a serious **AI-powered MCP Server Builder** whose core promise is:

> **Paste a URL. Get a real MCP server.**
