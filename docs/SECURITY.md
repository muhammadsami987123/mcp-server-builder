# Security

This application's core function is to fetch arbitrary, user-supplied URLs and follow links
discovered inside them. That is treated as a serious security boundary, not an incidental detail.
This document maps the SSRF threat model to the actual implementation in
`app/services/url_fetcher.py`.

## Threat model

A user can submit any URL. Without protection, that URL — or a redirect it issues — could target:

- loopback addresses (`127.0.0.1`, `::1`) to reach services only meant to be reachable from the
  host itself;
- private/internal network ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, etc.) to reach
  internal infrastructure the deploying organization did not intend to expose;
- link-local addresses (`169.254.0.0/16`, `fe80::/10`), including cloud metadata endpoints
  (`169.254.169.254`, `metadata.google.internal`) that can leak instance credentials;
- a DNS name that resolves to one of the above at request time even though it looked like a
  public hostname (DNS rebinding) — or resolves to a public IP on the first lookup and a private
  one on a later redirect/re-check;
- an oversized or slow response, to exhaust memory or hold connections open (DoS);
- non-HTML/JSON/YAML content types that could be used to smuggle unexpected payloads through the
  parsing pipeline;
- an infinite or very long redirect chain;
- unbounded link-following across a documentation site (crawl amplification).

## What we protect against, and how

Mapped directly to `app/services/url_fetcher.py` and `app/config.py`:

- **Format validation before any network call.** `validate_url_format()` rejects empty/oversized
  URLs, anything not `http`/`https`, URLs with no hostname, and hostnames in the
  `config.BLOCKED_HOSTNAMES` denylist (`localhost`, `localhost.localdomain`,
  `metadata.google.internal`, `169.254.169.254`) — all before a socket is ever opened.
- **DNS-rebinding-safe resolution.** `_resolve_and_check()` resolves the hostname via
  `socket.getaddrinfo` and rejects the request if **any** returned address falls inside
  `config.BLOCKED_NETWORKS`. This list covers loopback (`127.0.0.0/8`, `::1/128`), RFC 1918
  private space (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local
  (`169.254.0.0/16`, `fe80::/10`), carrier-grade NAT (`100.64.0.0/10`), documentation/test ranges
  (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`, `198.18.0.0/15`), multicast/reserved
  (`224.0.0.0/4`, `240.0.0.0/4`), unspecified (`0.0.0.0/8`), IPv4-mapped IPv6
  (`::ffff:0:0/96`), and unique local IPv6 (`fc00::/7`).
- **Manual, re-validated redirects.** The `httpx.AsyncClient` is created with
  `follow_redirects=False`. Every redirect response is handled by hand: the `Location` header is
  resolved to an absolute URL, and `_validate_hop()` re-runs both the format check and the full
  DNS resolution/blocklist check on that new URL before it is ever connected to — so a redirect to
  a blocked address is rejected exactly like a direct request would be. The number of hops is
  capped at `config.MAX_REDIRECTS` (default 5); exceeding it raises `SSRFError`.
- **Response size cap.** The body is streamed via `response.aiter_bytes()` and accumulated
  in-memory; the moment it exceeds `max_size` (`config.MAX_RESPONSE_SIZE`, default 10MB) an
  `SSRFError` is raised and the connection is abandoned — the full oversized body is never
  buffered.
- **Content-Type restriction.** The response's `Content-Type` (ignoring parameters like charset)
  must be in `config.ALLOWED_CONTENT_TYPES` (`application/json`, `application/yaml`,
  `application/x-yaml`, `text/yaml`, `text/html`, `text/plain`) or the fetch is rejected.
- **Bounded crawling.** API discovery (`app/services/api_discovery.py`) caps the total number of
  pages it will fetch while looking for spec/doc links at `config.MAX_DISCOVERY_PAGES` (default
  10) — it does not recursively crawl an entire site.
- **Never execute fetched content.** Fetched HTML/JS is only ever parsed as text/DOM for
  extracting endpoint information (`documentation_parser.py`); it is never evaluated, rendered, or
  executed. Generated MCP server code is template-rendered from structured data, never built by
  interpolating raw fetched content into executable code.
- **A single choke point.** Every one of the above only has to be implemented once because
  `safe_fetch()` is the sole entry point for outbound requests against user-supplied URLs anywhere
  in the codebase — nothing else is permitted to call `httpx`/`requests` directly on user input.

## Secrets handling

- API keys (OpenAI, and any credentials a generated server needs) are read from environment
  variables only — never hardcoded, never logged, never embedded in generated source.
- Generated MCP servers read their own credentials (`API_BASE_URL`, `API_KEY`/`API_TOKEN`) from
  the environment at runtime via `.env`; the builder never writes a real secret into a generated
  file.
- Error responses returned to the client never include raw exception text, stack traces, or
  internal file paths — routes translate service exceptions into a clean `detail` message, and a
  global exception handler in `app/main.py` catches anything uncaught and logs the real error only
  server-side.

## What we explicitly do NOT protect against

- **Public API abuse.** Once a URL passes SSRF checks and reachable-address resolution, this
  application will fetch it like any HTTP client would — it does not defend the target site
  against being fetched (rate limiting the target is the target's job).
- **Malicious content within an allowed API response.** JSON/YAML/HTML content that passes the
  content-type and size checks is parsed as data, not sanitized as if it were going to be
  rendered as trusted markup elsewhere; it is not intended to be redisplayed unescaped in any
  context that would execute it.
- **The correctness or safety of the API being wrapped.** MCP Server Builder does not vet whether
  the target API itself is trustworthy, rate-limited sanely, or safe to call — it only protects
  the *fetching* step. Running a generated server still means trusting whatever credentials you
  supply it to talk to.
- **OAuth2 token acquisition.** The generated server does not implement an OAuth2 flow; it expects
  the user to supply a valid token/credential via environment variables. This is a manual step,
  not a security gap in the fetch path.
- **Vetted output review.** Generated code is syntax- and structure-validated
  (`app/services/validator.py`), not security-audited; running any generated server on a real API
  is still the responsibility of whoever deploys it — review before running, as with any
  generated code.

## Testing SSRF protection

```bash
# Should fail — blocked loopback address
curl -X POST http://localhost:8000/api/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "http://127.0.0.1:9000"}'

# Should succeed — public API
curl -X POST http://localhost:8000/api/discover \
  -H "Content-Type: application/json" \
  -d '{"url": "https://api.github.com"}'
```

The automated coverage for this lives in `tests/test_security.py` — see `docs/TESTING.md`.
