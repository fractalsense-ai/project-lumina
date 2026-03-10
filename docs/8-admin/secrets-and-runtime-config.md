# secrets-and-runtime-config

Production-safe runtime configuration for Project Lumina.

## Goal

Use environment injection for secrets in staging/production, never committed secret files.

## Runtime modes

- Deterministic mode: no provider API key required (`deterministic_response=true`).
- Live LLM mode: provider API key is required (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`).

## Required production variables

- `LUMINA_RUNTIME_CONFIG_PATH`
- `LUMINA_JWT_SECRET`

Conditionally required:

- `OPENAI_API_KEY` when `LUMINA_LLM_PROVIDER=openai`
- `ANTHROPIC_API_KEY` when `LUMINA_LLM_PROVIDER=anthropic`

## Recommended production variables

- `LUMINA_LLM_PROVIDER`
- `LUMINA_OPENAI_MODEL` or `LUMINA_ANTHROPIC_MODEL`
- `LUMINA_ENFORCE_POLICY_COMMITMENT=true`
- `LUMINA_BOOTSTRAP_MODE=false`
- `LUMINA_CORS_ORIGINS`
- `LUMINA_PORT`

## Local development setup

1. Copy template:

```bash
cp .env.example .env
```

2. Fill `.env` values with local secrets and runtime settings.

3. Export variables in your shell or deployment launcher.

PowerShell example:

```powershell
$env:LUMINA_RUNTIME_CONFIG_PATH = "domain-packs/education/runtime-config.yaml"
$env:LUMINA_LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "<your-local-key>"
$env:LUMINA_JWT_SECRET = "<32-byte-or-longer-random-secret>"
```

POSIX example:

```bash
export LUMINA_RUNTIME_CONFIG_PATH="domain-packs/education/runtime-config.yaml"
export LUMINA_LLM_PROVIDER="openai"
export OPENAI_API_KEY="<your-local-key>"
export LUMINA_JWT_SECRET="<32-byte-or-longer-random-secret>"
```

## Generate a JWT secret

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Production deployment guidance

- Inject secrets through your platform secret manager (for example: container orchestrator secrets, CI/CD secret store, cloud app settings).
- Do not store provider keys or JWT secrets in committed files.
- Rotate `LUMINA_JWT_SECRET` and provider keys periodically and after incidents.
- Keep `LUMINA_BOOTSTRAP_MODE=false` after initial provisioning.

## Related docs

- [installation-and-packaging](../1-commands/installation-and-packaging.md)
- [lumina-api-server(2)](../2-syscalls/lumina-api-server.md)
- [rbac-administration](rbac-administration.md)
