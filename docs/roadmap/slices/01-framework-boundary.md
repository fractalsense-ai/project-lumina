---
version: 1.0.0
last_updated: 2026-05-05
---

# Slice 1: Framework Boundary and Final Shape Documentation

**Version:** 1.0.0
**Status:** Active
**Last updated:** 2026-05-05
**PR:** This document is itself the primary deliverable of Slice 1.

---

## Purpose

Make the Lumina Framework boundary explicit so that future implementation PRs
and coding agents do not mistake provisional domain/testing/deployment packs
for base framework infrastructure.

The repository is being finalised into a reusable base framework. Before any
extraction, removal, or restructuring work proceeds, the framework boundary
must be documented clearly and unambiguously.

---

## Scope

- Document that the final base framework consists of exactly three model packs:
  **System Model Pack**, **Coding Agent Model Pack**, and **Template Model Pack**.
- Document the role of each base pack at a high level.
- Document the single-ingress invariant: the Coding Agent has exactly one
  ingress point — the System Pack.
- Document the governance invariant: mechanical test passage does not equal
  activation approval; developer authorisation at the System Pack level is a
  separate required gate.
- Document the ephemeral-environment invariant: evidence is harvested before
  teardown; teardown failure is a ledgered escalation event.
- Warn clearly that all other packs currently in the repository (education,
  agriculture, assistant) are provisional domain/testing/scaffolding material
  and are not part of the base framework contract.
- Note that future PRs may extract, move, or remove non-base packs, but this
  PR does not perform that work.
- Establish the PR-per-slice roadmap convention so later PRs can continue from
  Slice 2.

---

## Out of Scope

- Implementing any framework code.
- Deleting, moving, or extracting domain/testing/experimental packs.
- Creating the Coding Agent Model Pack skeleton (planned for a later slice).
- Implementing schemas, state machines, ledgers, provider abstraction, or
  teardown logic.
- Cross-deployment federation, shared shape recognition, or thermodynamic
  ephemeral keys.

---

## Required Changes

### New files

| File | Purpose |
|------|---------|
| `docs/7-concepts/framework-boundary.md` | Authoritative framework boundary contract: three base packs, roles, invariants, governance posture |
| `docs/roadmap/README.md` | Roadmap index listing all slices and their status |
| `docs/roadmap/slices/01-framework-boundary.md` | This file — Slice 1 planning record |

### Updated files

| File | Change |
|------|--------|
| `docs/7-concepts/README.md` | Added `framework-boundary` row to the Section 7 concept table |
| `docs/README.md` | Added roadmap reference in the quick-start table |
| `docs/MANIFEST.yaml` | Added entries for all three new documentation files |

---

## New/Changed Contracts

This slice is documentation-only. No code contracts are created or modified.

The following **conceptual contracts** are established for future implementation
slices to conform to:

### Three-pack base framework

```
Base framework = { System Model Pack, Coding Agent Model Pack, Template Model Pack }
```

Every other pack is domain/deployment/testing material until explicitly promoted
or extracted.

### Request lifecycle (authoritative shape)

```
Natural language request
  -> intent classification
  -> System Pack authority gate
  -> actionable plan / task graph
  -> physics proposal and/or tooling build request
  -> deterministic validation
  -> test / stage
  -> developer authorization (System Pack gate)
  -> registration
  -> harvest test evidence
  -> ledger commitment
  -> teardown temporary environment
  -> teardown confirmation
  -> activation
```

### Build state machine (authoritative state names)

```
Requested → Scoped → Templated → Building → Built
  → Testing → Tested → Staged → AwaitingApproval
  → Registered → HarvestingEvidence → EvidenceCommitted
  → TearingDown → TeardownConfirmed → Active

Terminal: Failed | Escalated
Optional failure/exception: EvidenceHarvestFailed | LedgerCommitFailed
                           | TeardownFailed | CleanupEscalated
```

### Foundational invariants

1. **Single ingress.** The Coding Agent has exactly one ingress: the System Pack.
2. **Mechanical correctness ≠ governance approval.** Tests stage; authorisation activates.
3. **Destroy temporary surfaces, preserve their proof.** Evidence is harvested
   before teardown. Teardown failure is a ledgered escalation event.
4. **Separation of factory from governance.** Coding Agent manufactures; System
   Pack governs lifecycle.

---

## Files Likely Touched

```
docs/
  7-concepts/
    framework-boundary.md          ← NEW
    README.md                      ← UPDATED (new row in concept table)
  roadmap/
    README.md                      ← NEW
    slices/
      01-framework-boundary.md     ← NEW (this file)
  README.md                        ← UPDATED (roadmap reference)
  MANIFEST.yaml                    ← UPDATED (new doc entries)
```

---

## Acceptance Criteria

- [ ] `docs/7-concepts/framework-boundary.md` exists and states that the base
      framework consists of exactly System Model Pack, Coding Agent Model Pack,
      and Template Model Pack.
- [ ] The boundary document warns that other packs in the repository
      (education, agriculture, assistant) are provisional/experimental/domain
      material and are not part of the final base framework contract.
- [ ] The boundary document explains that future PRs may extract/remove/move
      non-base packs, but this PR does not perform that work.
- [ ] The boundary document makes clear that the Coding Agent has exactly one
      ingress: the System Pack.
- [ ] The boundary document preserves the governance invariant that mechanical
      correctness/testing does not equal activation approval.
- [ ] `docs/roadmap/slices/01-framework-boundary.md` exists with all required
      sections: Purpose, Scope, Out of Scope, Required Changes, New/Changed
      Contracts, Files Likely Touched, Acceptance Criteria, Tests,
      Ledger/Governance Impact, Follow-Up Slices.
- [ ] `docs/7-concepts/README.md` references `framework-boundary`.
- [ ] `docs/README.md` references the roadmap so it is discoverable.
- [ ] `docs/MANIFEST.yaml` includes entries for all new documentation files.
- [ ] No code was deleted, moved, or extracted as part of this slice.
- [ ] Repo integrity checks (`verify_repo.py`) continue to pass.

---

## Tests

This slice is documentation-only. No new automated tests are created.

Validation performed:

1. **Repo integrity check** — `python model-packs/system/controllers/verify_repo.py`
   must pass (it checks `docs/` structure and relative link validity).
2. **Manual review** — Confirm all acceptance criteria above are satisfied by
   inspecting the new and updated files.

If a markdown linter is added to the repository in a future slice, it should
be applied to these files at that time.

---

## Ledger/Governance Impact

This slice introduces no ledger writes and no state machine transitions. It
is purely additive documentation.

The governance impact is **clarification**: future implementation slices,
coding agents, and contributors now have an unambiguous written record of
what the base framework is, what is provisional, and what the authoritative
lifecycle shape looks like.

---

## Follow-Up Slices

The following slices are expected to follow Slice 1. Exact numbering and
scope will be confirmed in each slice's planning document.

| Slice | Anticipated Title |
|-------|-------------------|
| 02 | System Update Vocabulary — formal request type contracts (`SystemUpdateRequest`, `PhysicsEditProposal`, `ToolingBuildRequest`, `BuildResult`, `ActivationRecord`) |
| 03 | Request Intake and Classification — classify natural-language update requests into structured `SystemUpdateRequest` objects |
| 04 | System Pack Authority Gate — authority validation, scope resolution, requester role checks |
| 05 | Physics Edit Proposal Path — natural-language-to-physics-proposal flow |
| 06 | Physics Validation Harness — deterministic pre-approval checks |
| 07 | Physics Ledger and Rollback — proposal/activation lifecycle logging and rollback |
| 08 | Library Structure Refactor — two-tier `lib/` scope (model-pack level and module level) |
| 09 | Coding Agent Model Pack Skeleton — thin factory pack creation under `model-packs/coding-agent/` |
| 10 | Multi-Provider Model Abstraction — provider-agnostic model request/response contract |
| 11 | Per-Station Model Selection — pack-declared model preferences per planning/build/ops station |
| 12 | Model Selection Cascade — runtime resolution order: deployment → pack → module → system default |
| 13 | Planning LLM and Task Graph — structured task graph output from planning stage |
| 14 | Template Injection Contract — template class registry; System Pack selects, Coding Agent fills |
| 15 | Build State Machine — implement the full state machine defined in this slice |
| 16 | Failure Threshold and Escalation — configurable retry threshold, structured escalation, developer context reinjection |
| 17 | Test Runner and Artifact Validation — deterministic `BuildResult` generation |
| 18 | Developer Authorization Gate — System Pack authorization after test passage |
| 19 | Vectorized Success/Failure Index — Coding Agent pack institutional memory |
| 20 | Registration Handshake — System Pack registration of new surfaces after authorization |
| 21 | Post-Registration Evidence Harvest and Environment Teardown — log harvest, ledger commit, teardown, confirmation |
| 22 | Framework-Level Vectorized Ledger — framework-scoped operational pattern indexing |
