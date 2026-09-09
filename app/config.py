"""Application configuration, environment loading, and security thresholds."""

import ipaddress
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# --- Server ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# --- Security / SSRF thresholds ---
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "20"))
MAX_RESPONSE_SIZE = int(os.getenv("MAX_RESPONSE_SIZE", str(10 * 1024 * 1024)))  # 10MB
MAX_DISCOVERY_PAGES = int(os.getenv("MAX_DISCOVERY_PAGES", "10"))
MAX_REDIRECTS = int(os.getenv("MAX_REDIRECTS", "5"))
ALLOWED_CONTENT_TYPES = (
    "application/json",
    "application/yaml",
    "application/x-yaml",
    "text/yaml",
    "text/html",
    "text/plain",
)

# Private / reserved / loopback / link-local ranges that must never be reachable
# from a user-supplied URL. Applied to every resolved IP address for a hostname.
BLOCKED_NETWORKS = [
    ipaddress.ip_network(net)
    for net in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
        "::ffff:0:0/96",
    )
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "169.254.169.254",
}

# --- API discovery ---
OPENAPI_CANDIDATE_PATHS = (
    "/openapi.json",
    "/openapi.yaml",
    "/openapi.yml",
    "/swagger.json",
    "/swagger.yaml",
    "/api-docs",
    "/api-docs.json",
    "/v1/openapi.json",
    "/v2/openapi.json",
    "/docs/openapi.json",
    "/.well-known/openapi.json",
)

DOC_LINK_KEYWORDS = (
    "api",
    "docs",
    "documentation",
    "reference",
    "swagger",
    "openapi",
    "endpoint",
    "developer",
)

# --- Storage ---
DATA_DIR = BASE_DIR / "app" / "data"
PROJECTS_DIR = DATA_DIR / "projects"
GENERATED_DIR = BASE_DIR / "generated-projects"
DEMO_SPEC_PATH = BASE_DIR / "app" / "data" / "demo_openapi.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
