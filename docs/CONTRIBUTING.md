# Contributing

## Branch naming

```
<type>/<short-description>
```

Where `<type>` is one of `feature`, `fix`, `refactor`, `docs`, `test`, or `chore`. Examples:
`feature/graphql-discovery`, `fix/ssrf-redirect-revalidation`, `docs/deployment-notes`.

## Before opening a PR

Run the full quality gate from the repo root:

```bash
pytest              # tests must pass
black app/ tests/    # format
isort app/ tests/    # import sorting
mypy app/            # type checking
```

All four must be clean. If a pre-existing failure is unrelated to your change, call it out in the
PR description rather than silently working around it.

## Secrets

- Never commit `.env`, API keys, or any credential — `.env.example` documents the shape, real
  values only ever live in your local `.env` (gitignored) or your deployment's secret store.
  the OPENAI_API_KEY value and any user-supplied API credentials must never appear in logs,
  commit history, or generated code.
- If you accidentally commit a secret, rotate it immediately — don't just remove it in a follow-up
  commit, git history still has it.

## Scope discipline

- Keep changes focused on the files your task actually requires; don't refactor unrelated code in
  the same PR.
- Match the existing code's conventions (async I/O throughout the request path, Pydantic models
  for all external input/output, no fabricated data — see the anti-hallucination rule in
  `AGENTS.md`).
- Add or update tests alongside any behavior change — see `docs/TESTING.md` for what's covered
  where.

## Commit messages

Short, imperative summary line, optionally followed by a blank line and more detail:

```
Add Swagger 2.0 formData parameter parsing

Maps formData-in parameters to ParamLocation.BODY since there's no
first-class formData location in the internal model.
```
