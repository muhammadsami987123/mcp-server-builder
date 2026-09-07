# Changelog

All notable changes to MCP Server Builder will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-01

### Added
- Initial release of MCP Server Builder
- Web UI for API URL input and project browsing
- FastAPI backend with async support
- API discovery service (OpenAPI 3.0 and Swagger 2.0 support)
- API analysis service for endpoint extraction
- AI-driven MCP tool design using GPT-4
- Jinja2-based code generation for MCP servers
- Generated server validation (syntax and schema checks)
- SSRF protection with IP blocklist
- URL validation and security checks
- Project storage with JSON persistence
- Project history and listing
- ZIP download of generated projects
- Comprehensive documentation (README, ARCHITECTURE, SECURITY, etc.)
- Test suite with 80%+ coverage
- Docker support
- Deployment guide for production
- Contributing guidelines
- MIT License

### Features
- **URL Input**: Simple interface for entering API documentation URLs
- **Smart Discovery**: Automatically detects OpenAPI specs and Swagger definitions
- **AI Design**: Uses GPT-4 to design optimal MCP tool interfaces
- **Code Generation**: Produces complete, runnable MCP server code
- **Validation**: Ensures generated code is syntactically valid and MCP-compliant
- **Project Browser**: View and download generated projects in-browser
- **History**: Track all generated MCP servers with metadata
- **Security**: SSRF protection, API key safety, input validation

### Technical Stack
- Frontend: HTML5, Tailwind CSS, Vanilla JavaScript
- Backend: Python 3.8+, FastAPI, Uvicorn
- Data Validation: Pydantic v2
- AI: OpenAI GPT-4 API
- HTTP: httpx with async support
- Templates: Jinja2
- Development: pytest, black, mypy, flake8

### Documentation
- README.md – Project overview and quick start
- QUICKSTART.md – 5-minute setup guide
- ARCHITECTURE.md – Technical architecture and design
- API_REFERENCE.md – Complete API documentation
- SECURITY.md – Security model and threat mitigation
- TESTING.md – Testing guide and best practices
- CONTRIBUTING.md – Contribution guidelines
- DEPLOYMENT.md – Production deployment guide
- CLAUDE.md – Developer context for AI assistants
- AGENT.md – Instructions for AI agents working on the project

### Limitations (Known)
- Single API per project (multi-API composition in future)
- REST/OpenAPI only (GraphQL support planned)
- JSON file storage (PostgreSQL for >10k projects)
- No user authentication (coming in v0.2)
- No rate limiting per user (infrastructure ready)

## Planned Features

### v0.2.0 (Q1 2024)
- [ ] User authentication (API keys)
- [ ] Project sharing and collaboration
- [ ] Tool customization UI (edit designs before generation)
- [ ] GraphQL API support
- [ ] CLI for headless generation
- [ ] Automated testing for generated servers

### v0.3.0 (Q2 2024)
- [ ] Multi-API composition
- [ ] WebSocket/real-time API support
- [ ] Server hosting and one-click deployment
- [ ] Community-contributed server templates
- [ ] Advanced caching and performance optimization

### v0.4.0+ (Future)
- [ ] Database migration (PostgreSQL)
- [ ] Rate limiting and quota management
- [ ] Analytics and usage tracking
- [ ] Marketplace for generated servers
- [ ] Custom code generation templates

## Migration Guide

N/A – Initial release

## Deprecations

N/A – Initial release

## Security

- Fixed: No known security vulnerabilities in v0.1.0
- For security issues, email: security@example.com

## Contributors

- **Muhammad Sami Asghar Mughal** – Creator and Lead Developer

## License

MIT License – See LICENSE file for details

---

### How to Read This File

- **Added** – New features
- **Changed** – Changes in existing functionality
- **Deprecated** – Soon-to-be removed features
- **Removed** – Removed features
- **Fixed** – Bug fixes
- **Security** – Security updates

For updates and new releases, watch this repository or check the GitHub Releases page.
