# Deployment

## Development

```bash
uvicorn app.main:app --reload --port 8000
```

Auto-reloads on file changes. Use this for local development only.

## Staging / Production

Run with Gunicorn managing Uvicorn workers:

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --env PYTHONUNBUFFERED=1
```

Adjust `--workers` to roughly `(2 x CPU cores) + 1`. Since discovery/generation are I/O-bound and
async, a modest worker count handles significant concurrent load; scale further based on observed
latency (see `AGENTS.md` / `docs/ARCHITECTURE.md` for the request flow that drives this).

`gunicorn` is not in `requirements.txt` (it's a production-only dependency) — install it
separately in your deployment image:

```bash
pip install gunicorn
```

## Required environment variables

From `.env.example` — set these in your production environment (not in a committed `.env` file):

```bash
OPENAI_API_KEY=sk-...          # required for AI tool design; Demo Mode works without it
OPENAI_MODEL=gpt-4.1-mini

HOST=0.0.0.0
PORT=8000
DEBUG=false                     # must be false in production
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-domain.example   # do not leave as "*" in production

REQUEST_TIMEOUT=20
MAX_RESPONSE_SIZE=10485760      # 10MB — SSRF/DoS guard, see docs/SECURITY.md
MAX_DISCOVERY_PAGES=10
MAX_REDIRECTS=5
```

## Persistent storage

MCP Server Builder stores state as files on disk, not in a database:

- `app/data/projects/` — one JSON file per `MCPProject` (project metadata, discovery/design/
  generation/validation state).
- `generated-projects/` — the actual generated MCP server files per project, plus the ZIP archives
  built on download.

**Both directories need a writable volume in production.** In a containerized deployment, mount a
persistent volume at these paths (or an equivalent absolute location referenced by
`config.DATA_DIR` / `config.GENERATED_DIR`) — without it, every project a user builds disappears
on container restart/redeploy, and history/download links will 404.

If you run multiple instances behind a load balancer, these directories must be on shared storage
(e.g. a shared network volume) or requests for a given project must be sticky-routed to the
instance that generated it — there is no cross-instance project sync built in (see "JSON File
Storage" trade-offs in `CLAUDE.md`).

## Health check

`GET /health` returns `{"status": "ok"}` — wire this into your platform's liveness/readiness
probe.

## Monitoring

- Log generation times and success/failure rates per stage (discover/analyze/design/generate/
  validate).
- Alert on repeated 500-level responses — the global exception handler in `app/main.py` logs the
  real exception server-side even though the client only sees `{"detail": "Internal error"}`.
- Track OpenAI usage/cost if `OPENAI_API_KEY` is configured — tool design is the only step that
  calls out to OpenAI.
