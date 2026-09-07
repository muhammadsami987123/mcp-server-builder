# Contributing to MCP Server Builder

Thank you for your interest in contributing! This guide explains how to set up your environment, contribute code, and submit pull requests.

## Code of Conduct

Be respectful, inclusive, and professional. We value contributions from people of all backgrounds and experience levels.

## Getting Started

### Prerequisites

- Python 3.8+
- Git
- Virtual environment experience
- Basic understanding of FastAPI and async Python

### Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/marsaempower/mcp-server-builder.git
cd mcp-server-builder

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov black isort mypy flake8

# 4. Set up environment
cp .env.example .env
# Edit .env with your OpenAI API key

# 5. Verify installation
python -c "import app; print('✓ Import successful')"

# 6. Run tests
pytest
```

## Development Workflow

### 1. Create Feature Branch

```bash
# Always branch from main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/add-graphql-support
# Or: git checkout -b fix/ssrf-bypass
# Or: git checkout -b docs/update-readme
```

**Branch Naming Convention**:
- `feature/description` – New feature
- `fix/description` – Bug fix
- `docs/description` – Documentation
- `refactor/description` – Code refactoring
- `test/description` – Test improvements

### 2. Make Changes

Follow these principles:
- **Small commits**: Logical, focused changes
- **Tests first**: Write tests before code (TDD)
- **One feature per PR**: Don't mix multiple features
- **Update docs**: If behavior changes, update documentation

```bash
# Make changes
# Add tests
# Run tests locally

pytest --cov=app
```

### 3. Code Quality

Before committing, ensure code quality:

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Type check
mypy app/

# Lint
flake8 app/

# All together
make format lint type  # If Makefile exists
```

### 4. Commit Message Format

Write clear, descriptive commit messages:

```
[service] Brief description (50 chars max)

Longer explanation if needed (72 char wrap).
Explain WHY, not WHAT.

- Bullet point 1
- Bullet point 2

Fixes: #123
Related: #456
```

**Examples**:

```
[discovery] Add support for RAML API specifications

Extends discovery service to detect and parse RAML 1.0
definitions. Includes automatic detection of RAML files
and recursive inclusion handling.

Tests added for:
- RAML 1.0 specification parsing
- Included file resolution
- Common path detection

Fixes: #45
```

```
[security] Fix SSRF bypass via hostname aliases

Previously, IPv6 addresses were not checked against
blocklist. Added IPv6 support to IP validation.

Before:
  http://[::1] → Would bypass check

After:
  http://[::1] → Correctly blocked

Fixes: #123
```

### 5. Push and Create PR

```bash
# Push feature branch
git push origin feature/add-graphql-support

# Create PR on GitHub
# Or use gh CLI:
gh pr create --title "Add GraphQL support" \
  --body "Adds OpenAPI/Swagger-like discovery for GraphQL APIs"
```

## Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Tests pass: `pytest --cov=app`
- [ ] Code formatted: `black app/ tests/`
- [ ] Imports sorted: `isort app/ tests/`
- [ ] Types checked: `mypy app/`
- [ ] No linting errors: `flake8 app/`
- [ ] New tests added for new logic
- [ ] Existing tests still pass
- [ ] Documentation updated if needed
- [ ] Commit messages follow format
- [ ] Branch is up-to-date with main
- [ ] No merge conflicts

## Testing Guidelines

### Test Coverage

**Targets**:
- Services (discovery, analyzer, etc.): 90%+
- Models: 100%
- Utils: 85%+
- Routes: 75%+

### Test Organization

```python
# tests/test_something.py

import pytest
from app.services.something import some_function

class TestSomeFunction:
    """Test suite for some_function"""
    
    def test_happy_path(self):
        """Test normal operation"""
        result = some_function(valid_input)
        assert result is not None
    
    def test_error_case(self):
        """Test error handling"""
        with pytest.raises(ValueError):
            some_function(invalid_input)
    
    @pytest.mark.parametrize("input,expected", [
        ("a", 1),
        ("b", 2),
    ])
    def test_multiple_cases(self, input, expected):
        """Test multiple scenarios"""
        assert some_function(input) == expected
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test
pytest tests/test_security.py::test_ssrf_blocks_loopback

# Only fast tests (skip slow/integration)
pytest -m "not slow"

# Watch mode (auto-run on file change)
ptw
```

## Code Style Guide

### Python

Follow **PEP 8** with these overrides:

```python
# Line length
# Black enforces 100 character limit

# Imports
# Use isort (alphabetical, grouped)
from typing import Dict, List
import os
from pydantic import BaseModel
from app.models import something

# Type hints (required for new code)
def process_data(items: List[str]) -> Dict[str, int]:
    return {item: len(item) for item in items}

# Docstrings (for public functions/classes)
def discover_api(url: str) -> DiscoveryResult:
    """Discover API documentation at given URL.
    
    Args:
        url: HTTPS URL to API documentation
    
    Returns:
        DiscoveryResult containing discovered API structure
    
    Raises:
        ValueError: If URL format invalid
        SecurityError: If URL points to blocked IP range
    """

# Constants
MAX_RETRIES = 3
BLOCKED_IPS = ["127.", "192.168."]

# Classes
class APIRepresentation(BaseModel):
    """Represents discovered API."""
    pass

# Private functions (leading underscore)
def _helper_function():
    pass
```

### Async/Await

```python
# Use async for I/O operations
async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

# Test async code
@pytest.mark.asyncio
async def test_fetch_url():
    result = await fetch_url("https://example.com")
    assert result is not None
```

### Error Handling

```python
# Custom exceptions
class DiscoveryError(Exception):
    """Base class for discovery errors"""
    pass

class SSRFError(DiscoveryError):
    """SSRF protection violation"""
    pass

# Use specific exceptions
try:
    data = parse_json(response)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON: {e}")
    raise DiscoveryError(f"Invalid JSON response") from e

# Don't catch all exceptions
# Bad:
try:
    something()
except Exception:
    pass  # Never do this

# Good:
try:
    something()
except SpecificError:
    handle_error()
```

## Documentation

### Docstrings

All public functions/classes must have docstrings:

```python
def analyze_endpoints(api: APIRepresentation) -> List[Endpoint]:
    """Analyze and normalize API endpoints.
    
    Extracts endpoint information from API representation,
    normalizes paths and parameters for MCP tool design.
    
    Args:
        api: APIRepresentation with discovered endpoints
    
    Returns:
        List of normalized Endpoint objects
    
    Raises:
        ValueError: If endpoints are malformed
    
    Example:
        >>> api = APIRepresentation(endpoints=[...])
        >>> endpoints = analyze_endpoints(api)
        >>> len(endpoints)
        5
    """
```

### README / ARCHITECTURE / etc.

If your change affects user experience or architecture:

- Update `README.md` (if user-facing)
- Update `ARCHITECTURE.md` (if architecture changes)
- Update `API_REFERENCE.md` (if adding/changing endpoints)
- Update `SECURITY.md` (if security-related)
- Add entry to `CHANGELOG.md`

## Release Process

Only maintainers create releases, but here's how it works:

1. Update version in `app/__version__.py`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v0.2.0`
4. Push: `git push origin main --tags`
5. GitHub Actions builds and publishes release

## Common Issues & Solutions

### Import Errors

```bash
# Problem: ModuleNotFoundError
# Solution: Install development dependencies
pip install -r requirements.txt
pip install -e .  # Install package in dev mode
```

### Test Failures

```bash
# Problem: Tests pass locally but fail in CI
# Solution: Ensure all dependencies installed
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Run same tests CI runs
pytest --cov=app
```

### Type Checking

```bash
# Problem: mypy errors
# Solution: Add type hints
# Before:
def process(data):
    return data

# After:
from typing import Any
def process(data: Any) -> Any:
    return data

# Or run mypy to see issues
mypy app/
```

### Code Style

```bash
# Problem: Code doesn't match style
# Solution: Format automatically
black app/ tests/
isort app/ tests/
```

## Getting Help

- **Questions**: Open GitHub Discussion
- **Bug Reports**: Open GitHub Issue with reproduction steps
- **Security Issues**: Email security@example.com (don't open public issues)
- **Chat**: Join our Slack workspace (if available)

## Reviewer Guidelines

When your PR is reviewed:

- **Constructive Feedback**: Reviewers provide helpful, actionable feedback
- **Approval**: Usually 1-2 approvals before merge
- **CI/CD**: All tests and checks must pass
- **Discussion**: Be open to suggestions and discuss tradeoffs

## Becoming a Maintainer

After several quality contributions, you may be invited to become a maintainer with:

- Ability to review PRs
- Ability to merge code
- Ability to release versions
- Responsibility for project health

## Thank You

Your contributions, no matter how small, are greatly appreciated! We're excited to have you in the community.

---

**Happy coding!** 🚀
