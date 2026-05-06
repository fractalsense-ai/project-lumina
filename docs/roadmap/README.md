---
version: 1.0.0
last_updated: 2026-05-05
---

# Lumina Framework Roadmap

**Version:** 1.0.0
**Status:** Active
**Last updated:** 2026-05-05

---

## Overview

The Lumina Framework roadmap is delivered one slice at a time. Each slice is
a focused, reviewable unit of work with explicit scope, contracts, and
acceptance criteria.

Slices are numbered sequentially. Each slice is documented in its own file
under `docs/roadmap/slices/` and delivered as a focused PR.

---

## Slice Index

| Slice | Title | Status |
|-------|-------|--------|
| [01](slices/01-framework-boundary.md) | Framework Boundary and Final Shape Documentation | Active |

---

## Roadmap Posture

The repository is being finalised into the reusable base framework. The final
base framework consists of exactly three model packs:

- **System Model Pack** — sole governance/authority/ingress layer
- **Coding Agent Model Pack** — bounded artifact factory
- **Template Model Pack** — reusable approved framework template shapes

Domain packs currently in the repository (education, agriculture, assistant)
are provisional scaffolding used while validating the framework shape. They
will be extracted, moved, or removed in later PRs.

See [`docs/7-concepts/framework-boundary.md`](../7-concepts/framework-boundary.md)
for the authoritative framework boundary contract.

---

## Convention

Each slice document uses the following structure:

```markdown
## Purpose
## Scope
## Out of Scope
## Required Changes
## New/Changed Contracts
## Files Likely Touched
## Acceptance Criteria
## Tests
## Ledger/Governance Impact
## Follow-Up Slices
```
