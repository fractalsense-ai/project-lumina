# RBAC Administration

**Version:** 1.0.0  
**Status:** Active  
**Last updated:** 2026-03-12  

---

## Overview

Project Lumina uses a chmod-style permission model with 6 canonical roles. Permissions are stored as 3-digit octal values in each module's domain-physics document.

## Roles

| Role | ID | Hierarchy | Default Mode | Description |
|------|----|-----------|--------------|-------------|
| Root / OS Admin | `root` | 0 | 777 | Full system access, bypasses all permission checks |
| Domain Authority | `domain_authority` | 1 | 750 | Owns and manages domain pack modules |
| IT Support | `it_support` | 2 | 644 | System configuration and user management |
| Quality Assurance | `qa` | 2 | 644 | Evaluation access, read-only to modules |
| Auditor | `auditor` | 2 | 644 | CTL and compliance read access |
| Standard User | `user` | 3 | 644 | Session execution only |

## Permission Model

Each module declares a permission block in its domain-physics document:

```yaml
permissions:
  mode: "750"           # owner=rwx, group=r-x, others=---
  owner: "da_lead_001"  # pseudonymous ID of owning domain authority
  group: "domain_authority"
  acl:
    - role: qa
      access: rx
      scope: evaluation_only
    - role: auditor
      access: r
      scope: ctl_records_only
```

### Octal Notation

| Digit | Binary | Permissions |
|-------|--------|-------------|
| 7 | 111 | rwx (read + write + execute) |
| 6 | 110 | rw- (read + write) |
| 5 | 101 | r-x (read + execute) |
| 4 | 100 | r-- (read only) |
| 0 | 000 | --- (no access) |

### Friendly Display

The octal mode `750` displays as `rwxr-x---`:
- **Owner** (first 3): `rwx` — full access
- **Group** (middle 3): `r-x` — read and execute
- **Others** (last 3): `---` — no access

## Bootstrap Mode

When `LUMINA_BOOTSTRAP_MODE=true` (default), the first user to register is automatically assigned the `root` role. Subsequent users register as `user` by default.

Disable after initial setup:

```bash
export LUMINA_BOOTSTRAP_MODE=false
```

## Managing Users

Users are managed through the API:

```bash
# Register
curl -X POST /api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secure_pass_123", "role": "user"}'

# Login
curl -X POST /api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secure_pass_123"}'

# View profile
curl -H "Authorization: Bearer <token>" /api/auth/me

# List users (root/it_support only)
curl -H "Authorization: Bearer <token>" /api/auth/users
```

## Manifest Integrity

The manifest integrity systools apply role-based restrictions separate from the module-level octal
permission model. These are system-level operations that act on `docs/MANIFEST.yaml` directly.

| Operation | API Endpoint | Permission | Allowed Roles |
|-----------|--------------|------------|---------------|
| Check integrity (read) | `GET /api/manifest/check` | Read (r) | `root`, `domain_authority`, `qa`, `auditor` |
| Regenerate hashes (write) | `POST /api/manifest/regen` | Write (w) | `root`, `domain_authority` |

The `auditor` role may inspect the manifest (read) but may **not** regenerate hashes (write). Regen
is a write operation that modifies `docs/MANIFEST.yaml` — it is restricted to roles with authoring
authority (`root` and `domain_authority`).

All `POST /api/manifest/regen` calls are recorded as a CTL `TraceEvent` on the `_admin` ledger for
full auditability.

From the command line, any authenticated user in an allowed role may also invoke the systools
directly:

```bash
# Check (auditor-accessible)
lumina-integrity-check
python -m lumina.systools.manifest_integrity check

# Regen (root / domain_authority only)
lumina-manifest-regen
python -m lumina.systools.manifest_integrity regen
```

## SEE ALSO

- [rbac-spec-v1](../../specs/rbac-spec-v1.md) — Full RBAC specification
- [auth(3)](../3-functions/auth.md) — JWT authentication module
- [permissions(3)](../3-functions/permissions.md) — Permission checker
- [domain-authority-roles](../../governance/domain-authority-roles.md) — Governance role definitions
