import os
from pathlib import Path

# Base configuration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR.parent / "templates"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4-turbo-preview"

# Security Configuration
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB
REQUEST_TIMEOUT = 20  # seconds
MAX_DISCOVERY_PAGES = 10
MAX_REDIRECTS = 5

# SSRF Protection - blocked IP ranges
BLOCKED_IP_PATTERNS = [
    # Localhost/Loopback
    "127.",
    "::1",
    # Private networks
    "10.",
    "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.",
    # Link-local
    "169.254.",
    # Multicast/Broadcast
    "224.", "225.", "226.", "227.", "228.", "229.", "230.", "231.",
    "232.", "233.", "234.", "235.", "236.", "237.", "238.", "239.",
    "240.", "241.", "242.", "243.", "244.", "245.", "246.", "247.",
    "248.", "249.", "250.", "251.", "252.", "253.", "254.", "255.",
]

# Common OpenAPI/Swagger detection paths
OPENAPI_PATHS = [
    "/openapi.json",
    "/swagger.json",
    "/v3/openapi.json",
    "/api/openapi.json",
    "/api/swagger.json",
    "/docs",
    "/api/docs",
    "/swagger/index.html",
    "/.well-known/openapi.json",
]

# Common documentation paths
DOCS_PATHS = [
    "/docs",
    "/api/docs",
    "/documentation",
    "/api/documentation",
    "/guide",
    "/reference",
]
