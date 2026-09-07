# Security – MCP Server Builder Security Documentation

Comprehensive security documentation covering threats, protections, and best practices.

## Overview

MCP Server Builder operates in a **threat-rich environment** (accepting arbitrary URLs) and implements multiple security layers to prevent exploitation.

### Security Layers

```
┌─────────────────────────────────────────────┐
│  Layer 1: SSRF Protection (IP Blocklist)   │
│  ↓ Validated safe? Proceed                  │
│  ↓ Blocked IP? Reject                       │
├─────────────────────────────────────────────┤
│  Layer 2: URL Validation (Format/Length)   │
│  ↓ HTTPS scheme? Proceed                    │
│  ↓ Invalid? Reject                          │
├─────────────────────────────────────────────┤
│  Layer 3: Response Limits (Size/Timeout)   │
│  ↓ Size OK? Proceed                         │
│  ↓ Too large? Stop download                 │
├─────────────────────────────────────────────┤
│  Layer 4: Redirect Validation (Max Hops)   │
│  ↓ 5 hops max, each validated               │
├─────────────────────────────────────────────┤
│  Layer 5: Code Validation (Syntax/Schema)  │
│  ↓ Generated code syntactically valid?     │
│  ↓ MCP schema compliant?                    │
└─────────────────────────────────────────────┘
```

## Security Threats & Mitigations

### 1. Server-Side Request Forgery (SSRF)

**Threat**: Attacker provides URL pointing to internal service (e.g., `http://127.0.0.1:9000`, `http://192.168.1.1:8080`)

**Attack Goal**: Access internal services, metadata endpoints, credentials

**Mitigation: IP Blocklist**
```python
# app/config.py
BLOCKED_IP_PATTERNS = [
    "127.",           # Localhost/Loopback
    "::1",            # IPv6 Loopback
    "10.",            # Private Class A (10.0.0.0/8)
    "172.16.",        # Private Class B (172.16.0.0/12)
    "172.17.",        # ...
    # ... up to 172.31
    "192.168.",       # Private Class C (192.168.0.0/16)
    "169.254.",       # Link-local (169.254.0.0/16)
    "224.",           # Multicast (224.0.0.0/4)
    # ... up to 255
]
```

**Mitigation: Hostname Resolution Check**
```python
# Resolve hostname to IP, check against blocklist
import socket
ip = socket.gethostbyname(hostname)
if is_blocked_ip(ip):
    raise SecurityError("SSRF blocked: private IP range")
```

**Mitigation: Redirect Validation**
```python
# When following redirects (max 5):
redirects = 0
url = user_provided_url
while redirect_count < 5:
    response = fetch(url)
    if response.is_redirect():
        url = response.headers.get('Location')
        # Validate new URL
        ip = resolve_hostname(parse_url(url).hostname)
        if is_blocked_ip(ip):
            raise SecurityError("Redirect to blocked IP")
        redirects += 1
    else:
        break
if redirects >= 5:
    raise SecurityError("Too many redirects")
```

**Testing**:
```bash
# Should all fail
curl -X POST http://localhost:8000/api/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "http://127.0.0.1:9000"}'          # Loopback
-d '{"url": "http://192.168.1.1:8080"}'          # Private
-d '{"url": "http://localhost"}'                 # Hostname resolves to 127.0.0.1
-d '{"url": "http://169.254.169.254"}'           # AWS metadata

# Should succeed
-d '{"url": "https://api.github.com"}'
-d '{"url": "https://1.1.1.1"}'
```

### 2. URL Validation & Injection

**Threat**: Malformed URLs, extremely long URLs, special characters

**Mitigation: URL Format Validation**
```python
def validate_url(url: str) -> str:
    """Validate URL format and scheme."""
    if not isinstance(url, str):
        raise ValueError("URL must be string")
    
    if len(url) > 2048:  # Max URL length
        raise ValueError("URL too long (max 2048 chars)")
    
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS URLs allowed")
    
    # Parse and validate
    parsed = urllib.parse.urlparse(url)
    if not parsed.hostname:
        raise ValueError("Invalid URL: no hostname")
    
    return url
```

### 3. Resource Exhaustion (DOS)

**Threat**: Large API responses, infinite redirects, discovery crawls

**Mitigation: Response Size Limit**
```python
# config.py
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB

# In fetch function
headers = await client.stream('GET', url, timeout=20)
total_size = 0
async for chunk in headers.aiter_bytes():
    total_size += len(chunk)
    if total_size > MAX_RESPONSE_SIZE:
        raise ValueError(f"Response exceeds {MAX_RESPONSE_SIZE} bytes")
    yield chunk
```

**Mitigation: Request Timeout**
```python
# Timeout after 20 seconds
response = await client.get(url, timeout=20)
```

**Mitigation: Discovery Page Limit**
```python
# config.py
MAX_DISCOVERY_PAGES = 10

# In discovery logic
pages_discovered = 0
while pages_discovered < MAX_DISCOVERY_PAGES:
    # Discover linked pages
    pages_discovered += 1
```

### 4. API Key Exposure

**Threat**: API keys leaked in logs, error messages, or generated code

**Mitigation: Environment Variable Storage**
```bash
# .env (never committed)
OPENAI_API_KEY=sk-...

# app/config.py
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")
```

**Mitigation: Logging Filter**
```python
import logging

class SensitiveDataFilter(logging.Filter):
    """Remove sensitive data from logs"""
    
    def filter(self, record):
        # Remove API keys
        record.msg = record.msg.replace(OPENAI_API_KEY, "***REDACTED***")
        return True

logger.addFilter(SensitiveDataFilter())
```

**Mitigation: Never Hardcode Keys in Generated Code**
```python
# Generated server config.py should use environment variables:
# CORRECT:
API_KEY = os.getenv("API_KEY")

# WRONG:
API_KEY = "sk-xxx"  # Never do this
```

**Testing**:
```bash
# Ensure API key never appears in logs
pytest -v --log-cli-level=DEBUG 2>&1 | grep -i "sk-"
# Should return no results
```

### 5. Code Injection in Generated Servers

**Threat**: Malicious code in API responses gets templated into generated server

**Example Attack**:
```
Attacker controls API response:
{
  "endpoints": [
    {
      "path": "/x'; import os; os.system('rm -rf /'); '",
      "method": "GET"
    }
  ]
}

Could result in generated code:
def handle_x(self):
    return self.client.get('/x'; import os; os.system('rm -rf /'); '')  # Injection!
```

**Mitigation: Input Sanitization**
```python
# Sanitize all user-controlled data before templating
def sanitize_path(path: str) -> str:
    """Remove special characters from API path"""
    # Only allow alphanumeric, dash, underscore, slash, braces
    if not re.match(r'^[\w/\{\}-]*$', path):
        raise ValueError(f"Invalid path: {path}")
    return path

def sanitize_name(name: str) -> str:
    """Ensure tool name is valid Python identifier"""
    if not name.isidentifier():
        raise ValueError(f"Invalid identifier: {name}")
    return name
```

**Mitigation: Jinja2 Escaping**
```jinja2
{# In templates, auto-escape strings #}
def handle_{{ tool.name }}(self):
    return self.client.request(
        method="{{ tool.method | e }}",  {# Escape special chars #}
        path="{{ tool.path | e }}"
    )
```

**Mitigation: Generated Code Validation**
```python
# Validate syntax before returning
try:
    compile(generated_code, 'main.py', 'exec')
except SyntaxError as e:
    raise ValueError(f"Generated code has syntax error: {e}")
```

### 6. Dependencies with Known Vulnerabilities

**Threat**: Using outdated packages with known CVEs

**Mitigation: Pin Dependency Versions**
```
# requirements.txt – use exact versions
fastapi==0.104.1          # Not: fastapi>=0.100.0
uvicorn==0.24.0           # Not: uvicorn
pydantic==2.5.0
openai==1.3.9
```

**Mitigation: Regular Updates**
```bash
# Check for vulnerabilities
pip install safety
safety check

# Update dependencies safely
pip list --outdated
pip install --upgrade package_name
```

### 7. Authentication & Authorization

**Current**: No authentication (public API)

**Future Considerations**:
- API key-based auth for rate limiting
- JWT tokens for user sessions
- OAuth2 for delegation
- Rate limiting per user/IP

### 8. CORS (Cross-Origin Resource Sharing)

**Configuration**:
```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**In Production**:
```python
allow_origins = os.getenv("CORS_ORIGINS", "").split(",")
# Only allow specific domains, not "*"
```

## Security Best Practices

### For Developers

1. **Never Commit Secrets**
   ```bash
   # Good
   cp .env.example .env
   edit .env
   
   # Bad
   git add .env  # Never do this
   ```

2. **Use Type Hints & Validation**
   ```python
   # Good – Pydantic validates automatically
   class DiscoverRequest(BaseModel):
       url: str  # Auto-validated by Pydantic
       timeout: int = 20
   
   # Bad – No validation
   def discover(url, timeout):
       # User could pass anything
   ```

3. **Log Carefully**
   ```python
   # Good
   logger.info(f"Discovering API at: {url}")
   
   # Bad
   logger.debug(f"Using API key: {OPENAI_API_KEY}")  # Never log secrets!
   ```

4. **Test Security Assumptions**
   ```python
   def test_ssrf_blocks_loopback():
       with pytest.raises(SecurityError):
           validate_url("http://127.0.0.1")
   ```

### For Operators (Running in Production)

1. **Environment Configuration**
   ```bash
   # Use environment variables, not .env
   export OPENAI_API_KEY=sk-...
   export DEBUG=false
   export CORS_ORIGINS=https://example.com
   ```

2. **HTTPS Enforcement**
   ```
   # Use reverse proxy (nginx, Caddy) to:
   - Enforce HTTPS
   - Handle SSL certificates
   - Rate limit requests
   - Log all requests
   ```

3. **Monitoring & Logging**
   ```
   - Log all API requests (URL, timestamp, status)
   - Alert on repeated SSRF attempts
   - Track failed validations
   - Monitor API key usage
   ```

4. **Rate Limiting**
   ```
   - Limit requests per IP
   - Limit OpenAI API calls
   - Queue requests if needed
   ```

### For Users (Using Generated Servers)

1. **Store API Keys Securely**
   ```bash
   # Good
   export MY_API_KEY=secret
   mcp install
   
   # Bad
   API_KEY = "secret" in config.py
   git push  # Oops, exposed!
   ```

2. **Review Generated Code**
   - Read main.py before running
   - Check for suspicious imports
   - Review tool implementations

3. **Test in Sandbox First**
   - Run generated server in isolated environment
   - Test with non-production credentials
   - Monitor for unexpected behavior

## Known Limitations

### Current Protections
- ✅ SSRF protection (IP blocklist)
- ✅ URL validation (HTTPS required)
- ✅ Response size limits
- ✅ Redirect validation
- ✅ Basic code injection prevention
- ✅ API key not logged

### Not Protected Against (Yet)
- ❌ DNS rebinding attacks (uses dns cache)
- ❌ Time-of-check-time-of-use (TOCTTOU) race conditions
- ❌ Compromised API upstream (if API serves malicious data)
- ❌ Side-channel attacks
- ❌ Exploits in dependencies (rely on updates)

## Reporting Security Issues

**IMPORTANT**: Do NOT open public GitHub issues for security vulnerabilities.

Instead:
1. Email: `security@example.com`
2. Include:
   - Vulnerability description
   - Steps to reproduce
   - Potential impact
   - Suggested fix (optional)

3. Expected response time: 48 hours

## Security Audit Checklist

- [ ] All external inputs validated (Pydantic)
- [ ] No hardcoded secrets (all in environment)
- [ ] API keys never logged
- [ ] SSRF protection tested with blocked IPs
- [ ] Response size limits enforced
- [ ] Generated code validated for syntax
- [ ] Dependencies pinned to exact versions
- [ ] Error messages don't expose internals
- [ ] HTTPS enforced (in production)
- [ ] CORS properly configured
- [ ] Rate limiting implemented (if needed)
- [ ] Security tests in CI/CD
- [ ] Regular dependency updates scheduled

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- CWE-918 (SSRF): https://cwe.mitre.org/data/definitions/918.html
- CWE-94 (Code Injection): https://cwe.mitre.org/data/definitions/94.html
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- NIST Cybersecurity Framework: https://www.nist.gov/cyberframework

---

**Last Updated**: 2024-01-01  
**Review Frequency**: Quarterly
