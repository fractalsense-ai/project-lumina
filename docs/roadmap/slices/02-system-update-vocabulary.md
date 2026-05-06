---
version: 1.0.0
last_updated: 2026-05-06
---

# Slice 2: System Update Vocabulary

**Version:** 1.0.0
**Status:** Active
**Last updated:** 2026-05-06
**PR:** This document is itself the primary deliverable of Slice 2.

---

## Purpose

Establish a canonical, shared vocabulary for all system update work handled by
the Lumina Framework, so that natural-language framework and domain update
requests are no longer treated as loose prompts.

Each term defined here becomes the shared language used by future slices for
intake, planning, authority review, validation, staging, registration,
activation, rollback, and ledger records. Subsequent slices implement the
behaviour described by these terms; this slice only names and contracts them.

---

## Scope

- Define the seven canonical vocabulary terms and their expected semantics:
  `SystemUpdateRequest`, `PhysicsEditProposal`, `ToolingBuildRequest`,
  `DomainLibraryUpdateProposal`, `RegistrationRequest`, `BuildResult`, and
  `ActivationRecord`.
- State the lifecycle relationship between these terms so future slices have an
  agreed ordering to implement against.
- Record the invariants that these terms encode (single ingress, mechanical
  correctness ≠ governance approval, activation ownership).
- Update the roadmap index so Slice 2 is discoverable.
- Register the new file in `docs/MANIFEST.yaml`.

---

## Out of Scope

- Implementing request classification. That is Slice 3.
- Implementing the authority gate. That is Slice 4.
- Implementing physics proposal validation. That is a later physics slice.
- Implementing Coding Agent invocation or model-pack skeletons.
- Implementing ledgers, rollback, provider abstraction, state machines,
  registration, or teardown.
- Removing or moving any experimental, domain, or test packs.

---

## Required Changes

### New files

| File | Purpose |
|------|---------|
| `docs/roadmap/slices/02-system-update-vocabulary.md` | This file — Slice 2 planning and contract vocabulary record |

### Updated files

| File | Change |
|------|--------|
| `docs/roadmap/README.md` | Added Slice 2 row to the Slice Index table |
| `docs/MANIFEST.yaml` | Added entry for this file |

---

## New/Changed Contracts

This slice is documentation-only. No executable code contracts are created or
modified.

The following **conceptual contracts** are established so that future
implementation slices have a single authoritative reference for each term.

---

## Contract Vocabulary

### `SystemUpdateRequest`

The canonical **intake-level object** representing a user- or
system-originated request to change framework or domain behaviour. It is the
structured output that Slice 3 classification will produce from a raw
natural-language input.

A `SystemUpdateRequest` is created *before* any mutation or build work begins.
Natural-language requests are converted into structured records; they are never
acted upon as loose prompts.

**Expected fields / concepts:**

| Field | Description |
|-------|-------------|
| `request_id` | Unique identifier for this request |
| `requester` | Identity of the user or system that originated the request |
| `request_source` | Channel or interface through which the request arrived |
| `raw_request` | Original natural-language text, preserved verbatim |
| `classified_type` | Output of classification (e.g. `physics_edit`, `tooling_build`, `domain_library_update`) |
| `requested_scope` | Bounded scope resolved by the System Pack (pack, module, or surface affected) |
| `authority_context` | Requester's resolved authority level at time of classification |
| `status` | Current lifecycle status (e.g. `pending`, `classified`, `scoped`, `approved`, `rejected`) |
| `created_at` | ISO-8601 timestamp of request creation |
| `links_to_proposals_or_jobs` | References to downstream `PhysicsEditProposal`, `ToolingBuildRequest`, or other derived records |

Field names are indicative. Exact implementation fields are resolved in later
slices once the schema convention for this repository is confirmed.

---

### `PhysicsEditProposal`

A proposed, bounded change to model or domain **physics**: policy thresholds,
standing orders, invariants, escalation rules, or related non-executable
rule/specification material.

**Key invariant:**

> Natural-language physics changes produce proposals, not direct mutations.

A `PhysicsEditProposal` flows from a classified `SystemUpdateRequest`. It
represents *intent* that must survive authority review and validation before
any domain-physics artifact is mutated. The Coding Agent is not involved in
ordinary physics edits; the change path is:

```
SystemUpdateRequest (classified_type: physics_edit)
  -> PhysicsEditProposal
  -> schema validation
  -> invariant/conflict validation  (Slice 6)
  -> authority review               (Slice 4)
  -> domain-physics update + hash commitment
```

---

### `ToolingBuildRequest`

A fully scoped request, routed through the System Pack, asking the Coding
Agent to manufacture executable or supporting artifacts: tool adapters, API
endpoints, slash commands, module workflows, or generated tests.

**Key invariant:**

> The Coding Agent receives only fully scoped jobs through the System Pack.

A `ToolingBuildRequest` is the object that crosses the boundary from the
System Pack into the Coding Agent. It carries resolved scope, a selected
template reference, authority context, and all material the Coding Agent needs
to begin building. It is never constructed directly by a user or by an
external caller.

---

### `DomainLibraryUpdateProposal`

A proposal to update pack or module **library** material: reference
specifications, domain-supporting knowledge artifacts, or shared knowledge
held in a pack's `lib/` directory.

The term `lib/` is used throughout this document. Older documentation may
still use `domain-lib`; that terminology will be unified when the library
structure refactor lands (Slice 8 of the current roadmap). Until then, both
terms refer to the same concept.

A `DomainLibraryUpdateProposal` follows the same proposal-before-mutation
discipline as `PhysicsEditProposal`. Library material is not mutated directly
from natural language.

---

### `RegistrationRequest`

A request from the System Pack to **register** a staged, authorized artifact
into the framework's active surface. The artifact may be a new endpoint, slash
command, tool adapter, module workflow, manifest entry, or library artifact.

**Key distinction:**

> `registered` ≠ `active` unless all activation requirements are satisfied.

Registration records that an artifact has passed all mechanical and governance
gates and is ready for activation. Activation is a separate, governed step
(see `ActivationRecord` below).

---

### `BuildResult`

Structured output produced at the end of build, test, and validation
activity. It summarises what was built, what was verified, and what the
outcome was so the System Pack can make an informed governance decision.

**Expected summary content:**

- Artifact identity (name, version, type, hash/manifest)
- Build attempt count and final status
- Validation outcomes (schema, invariant, import, route/command dry-run, secret hygiene, permission boundary)
- Test results (pass / fail / skipped counts, test identifiers)
- Safety check results
- Staged / Failed / Escalated disposition

**Key invariant:**

> Mechanical correctness and test passage **stage** an artifact. They do not
> approve activation.

A `BuildResult` with `disposition: staged` means the artifact is ready for
human/governance review. It does not mean the artifact is live.

---

### `ActivationRecord`

A **governance record** proving who or what authorised activation, what
artifact (version and hash) was activated, what validations were considered,
when activation occurred, and how rollback or audit can locate the decision.

**Expected content:**

- Artifact identity (name, version, hash — must match the staged `BuildResult`)
- Authorising principal (human developer or System Pack authority context)
- Validations considered at activation time (by reference to `BuildResult`)
- Activation timestamp
- Rollback pointer (how to locate or reverse the activation)
- Ledger reference (where this record is durably committed)

**Key invariant:**

> Activation is owned by the **System Pack**, not the Coding Agent.

The Coding Agent manufactures and stages. The System Pack activates. An
`ActivationRecord` exists only after a human developer or the System Pack has
explicitly authorised the transition from `Staged` to `Active`.

---

## Lifecycle Diagram

The following diagram shows how the vocabulary terms relate to each other
across the update lifecycle. This is contract/vocabulary planning, not yet
executable orchestration.

```text
Natural-language request
  -> SystemUpdateRequest          (Slice 3: intake and classification)
       |
       +-- PhysicsEditProposal    (when classified_type is physics_edit)
       |     -> validation / authority review
       |     -> domain-physics update
       |
       +-- DomainLibraryUpdateProposal  (when classified_type is domain_library_update)
       |     -> validation / authority review
       |     -> lib/ artifact update
       |
       +-- ToolingBuildRequest    (when classified_type requires executable artifact)
             -> Coding Agent (via System Pack only)
             -> build / test / validate
             -> BuildResult
             -> developer / System Pack authorization
             -> RegistrationRequest
             -> ActivationRecord
```

The Coding Agent is only reached via `ToolingBuildRequest`. Physics and library
paths do not involve the Coding Agent. All paths begin with a structured
`SystemUpdateRequest`; no path begins with a raw natural-language string.

---

## Files Likely Touched

```
docs/
  roadmap/
    README.md                              ← UPDATED (Slice 2 row added)
    slices/
      02-system-update-vocabulary.md       ← NEW (this file)
  MANIFEST.yaml                            ← UPDATED (new entry added)
```

---

## Acceptance Criteria

- [ ] `docs/roadmap/slices/02-system-update-vocabulary.md` exists with all
      required sections.
- [ ] All seven vocabulary terms are defined: `SystemUpdateRequest`,
      `PhysicsEditProposal`, `ToolingBuildRequest`,
      `DomainLibraryUpdateProposal`, `RegistrationRequest`, `BuildResult`,
      `ActivationRecord`.
- [ ] Documentation states that natural-language requests are converted into
      structured records before mutation or build work begins.
- [ ] Documentation preserves the invariant that the System Pack is the only
      ingress to the Coding Agent (`ToolingBuildRequest` crosses that boundary;
      nothing else does).
- [ ] Documentation preserves the invariant that mechanical correctness and
      test passage do not equal governance approval.
- [ ] Documentation states that activation is owned by the System Pack, not
      the Coding Agent.
- [ ] The lifecycle diagram makes the ordering of the vocabulary terms clear.
- [ ] `docs/roadmap/README.md` includes a Slice 2 row in the Slice Index table.
- [ ] `docs/MANIFEST.yaml` includes an entry for this file.
- [ ] No code was deleted, moved, or extracted as part of this slice.
- [ ] Repo integrity checks (`verify_repo.py`) continue to pass.

---

## Tests

This slice is documentation-only. No new automated tests are created.

Validation performed:

1. **Repo integrity check** — `python model-packs/system/controllers/verify_repo.py`
   must pass.
2. **Manual review** — Confirm all acceptance criteria above are satisfied by
   inspecting the new and updated files.

No automated markdown linting is currently configured in this repository. If a
markdown linter is added in a future slice, it should be applied to these files
at that time.

---

## Ledger/Governance Impact

This slice introduces no ledger writes and no state machine transitions. It is
purely additive documentation.

The governance impact is **vocabulary lock-in**: future implementation slices,
coding agents, and contributors now have a single authoritative reference for
the seven canonical update-work terms. Using these terms consistently across
slices reduces ambiguity and prevents drift between how intake, build, and
activation steps are named and described.

---

## Follow-Up Slices

| Slice | Anticipated Title |
|-------|-------------------|
| 03 | Request Intake and Classification — classify natural-language update requests into `SystemUpdateRequest` objects |
| 04 | System Pack Authority Gate — authority validation, scope resolution, requester role checks |
| 05 | System Pack as Sole Coding Agent Ingress — enforce single-ingress invariant at the implementation level |
| 06+ | Physics Edit Proposal Path — natural-language-to-`PhysicsEditProposal` flow and validation |
