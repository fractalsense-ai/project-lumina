---
version: 1.0.0
last_updated: 2026-05-05
---

# framework-boundary(7) — Base Framework Packs and Boundary Contract

**Version:** 1.0.0
**Status:** Active
**Last updated:** 2026-05-05

---

## Name

framework-boundary — the contract that defines what belongs to the Lumina Framework
core and what belongs to domain/deployment/testing layers built on top of it.

## Synopsis

The Lumina Framework base layer consists of exactly **three model packs**:

| Pack | Role |
|------|------|
| System Model Pack | Sole governance, authority, and ingress layer |
| Coding Agent Model Pack | Bounded artifact factory |
| Template Model Pack | Reusable approved template shapes and contracts |

All other model packs currently present in the repository — including education,
agriculture, and assistant — are **provisional domain/deployment/testing
material**, not base framework infrastructure.

---

## Description

### A. The Three Base Framework Packs

The Lumina base framework is not a general-purpose collection of model packs.
It is a minimal, reusable engine layer with three purpose-built packs that every
deployment inherits. These three packs form the framework-core contract.

#### 1. System Model Pack (`model-packs/system/`)

The System Model Pack is the **sole governance and authority layer** of the
framework. All requests, activations, and registrations must pass through it.

Responsibilities:

- Validates authority: confirms that the requester has sufficient role/scope for
  the requested operation.
- Scopes requests: converts a raw user intent into a fully scoped job packet
  before handing it downstream.
- Gates activation and registration: a generated artifact cannot become active
  until the System Pack authorises it. Mechanical test passage is not
  sufficient — explicit developer authorisation at the System Pack level is
  required.
- Owns the escalation and governance surface: routes out-of-bounds conditions
  to the appropriate human authority rather than silently failing or
  proceeding.

**Invariant:** No model pack, user, or external caller reaches any other
framework component directly. All requests route through the System Pack.

#### 2. Coding Agent Model Pack (`model-packs/coding-agent/`)

The Coding Agent Model Pack is a **bounded artifact factory**. It receives
only fully scoped job packets from the System Pack and manufactures
executable and supporting files.

Responsibilities:

- Receives a scoped job (template selected, authority confirmed) from the
  System Pack.
- Produces executable artifacts, supporting files, test scaffolding, and
  manifests according to the job specification.
- Runs deterministic validation (schema checks, import validation, test
  execution) and produces a structured `BuildResult`.
- Submits staged artifacts back to the System Pack for authorization review;
  it does not activate or register anything directly.

**Invariant:** The Coding Agent has **exactly one ingress: the System Pack.**
It has no direct activation rights. It is pure factory infrastructure; all
domain meaning lives in the domain packs that own it.

> **Note:** The Coding Agent Model Pack skeleton does not yet exist in this
> repository. Its creation is planned for a later implementation slice. The
> architectural contract documented here is the authoritative specification
> it will conform to when built.

#### 3. Template Model Pack (`model-packs/template/`)

The Template Model Pack **owns the reusable, approved framework template
shapes and contracts** used by System Pack routing and Coding Agent
manufacturing workflows.

Responsibilities:

- Provides the canonical scaffold for each generatable artifact class (sensor
  adapters, API handlers, slash commands, module workflows, test templates,
  domain-lib reference specs, etc.).
- Acts as the authoritative shape registry: the Coding Agent fills approved
  templates; it does not invent domain shapes from nothing.
- Consumed by both the System Pack (template selection during job scoping) and
  the Coding Agent Pack (template injection during build).

---

### B. Framework Infrastructure vs. Domain/Deployment/Testing Packs

The three base packs defined above are **framework infrastructure**. They are
engine-level components that every Lumina deployment inherits unchanged.

All other model packs serve a different purpose:

| Category | Examples | Status |
|----------|----------|--------|
| Domain packs | education, agriculture, assistant | Provisional — not base framework |
| Deployment-specific packs | NOC, clinic, field operations | Provisional — not base framework |
| Experimental/testing packs | Any pack created during framework validation | Provisional — not base framework |

The packs currently present in `model-packs/` beyond the three base packs
(education, agriculture, assistant) are **temporary scaffolding** used while
validating the framework shape. They demonstrate that the engine works across
varied domains, but they are not part of the long-term framework-core
contract.

**They should be treated as experimental/domain/testing material until they
are extracted, moved to their own repositories, or removed in later PRs.**

---

### C. Governance Invariants

The following invariants apply across the entire base framework and must be
preserved in every implementation slice:

1. **Single ingress.** The Coding Agent has exactly one ingress: the System
   Pack. No model pack, user, or external caller bypasses this gate.

2. **Mechanical correctness ≠ governance approval.** Passing automated tests
   stages an artifact as a candidate. Developer authorisation at the System
   Pack level activates it. Both gates are required; neither alone is
   sufficient.

3. **Ephemeral environments are destroyed; their evidence is not.** Temporary
   build, test, and staging environments must be harvested for useful
   evidence, committed to the ledger, and torn down after registration.
   Teardown failure is a ledgered escalation event, never a silent lingering
   resource.

4. **Separation of factory from governance.** The Coding Agent Pack
   manufactures artifacts. The System Pack governs their lifecycle. These
   responsibilities are not shared or merged.

---

### D. Roadmap Posture

This document establishes the **boundary and final shape** of the Lumina base
framework. It does not implement that shape — the Coding Agent Pack skeleton
does not exist yet, and non-base domain packs have not been extracted or
removed.

Implementation proceeds slice by slice. Each slice is documented in
`docs/roadmap/slices/` and delivered as a focused PR. The slice documents
describe intent, scope, contracts, and acceptance criteria for each increment
of implementation work.

See [`docs/roadmap/slices/01-framework-boundary.md`](../roadmap/slices/01-framework-boundary.md)
for the Slice 1 planning record.

---

## See Also

- [lumina-framework-ontology(7)](lumina-framework-ontology.md) — engine,
  model-pack, and module vocabulary
- [domain-pack-anatomy(7)](domain-pack-anatomy.md) — seven-component anatomy
  of a model-pack
- [zero-trust-architecture(7)](zero-trust-architecture.md) — fail-closed
  defaults and authority posture
- [state-change-commit-policy(7)](state-change-commit-policy.md) — every
  state mutation must write a System Log record before returning success
- [docs/roadmap/slices/01-framework-boundary.md](../roadmap/slices/01-framework-boundary.md)
  — Slice 1 planning document
