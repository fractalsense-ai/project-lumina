---
version: 1.0.0
last_updated: 2026-05-07
---

# Slice 3: Request Intake and Classification

**Version:** 1.0.0
**Status:** Active
**Last updated:** 2026-05-07
**PR:** This document is itself the primary deliverable of Slice 3.

---

## Purpose

Define the intake and classification contract that converts a raw
natural-language system update request into a structured
[`SystemUpdateRequest`](02-system-update-vocabulary.md#systemupdaterequest)
(established in Slice 2).

Classification is the first governed step in the update lifecycle. It assigns
a `classified_type` to an incoming request, normalises its metadata, and
emits a structured record that downstream governance layers (authority gate,
physics validation, Coding Agent ingress) can act on. It does not grant
authority. It does not activate anything. It does not directly invoke the
Coding Agent. It does not mutate system state.

---

## Scope

- Document the intake flow from raw natural-language request to structured
  `SystemUpdateRequest`.
- Define the canonical initial classification types and their expected later
  routing implications.
- Document the `ClassificationRecord` output fields/concepts.
- Enumerate the governance and safety invariants that classification must
  preserve.
- Update the roadmap index so Slice 3 is discoverable.
- Register the new file in `docs/MANIFEST.yaml`.
- Optionally add lightweight enum/type scaffolding if the repository already
  has a schema/contracts convention (minimal, aligned with existing patterns).

---

## Out of Scope

- Implementing the authority gate. That is Slice 4.
- Implementing the dedicated sole-ingress enforcement layer. That is Slice 5.
- Implementing physics proposal validation or patching. That is Slice 6+.
- Implementing Coding Agent invocation or model-pack skeletons.
- Implementing template injection, build state machines, ledgers, rollback,
  registration, activation, or teardown.
- Removing or moving experimental, domain, or test packs.
- Implementing provider or model selection.

---

## Required Changes

### New files

| File | Purpose |
|------|---------|
| `docs/roadmap/slices/03-request-intake-and-classification.md` | This file — Slice 3 planning and contract record |

### Updated files

| File | Change |
|------|--------|
| `docs/roadmap/README.md` | Added Slice 3 row to the Slice Index table |
| `docs/MANIFEST.yaml` | Added entry for this file |

---

## Intake Flow

The classification pathway converts a natural-language update request into a
structured `SystemUpdateRequest` via the following steps:

```text
Natural-language request (raw text)
  -> preserve raw_request verbatim
  -> normalise request metadata
       (requester, request_source, received_at, context/channel identifiers)
  -> identify requester / source / context
  -> classify request type
       (assign classified_type from the canonical set — see Classification Types below)
  -> assign requested_scope
       (the pack, module, or surface the requester believes is affected)
  -> attach authority_context placeholder
       (requester's identity recorded; authority level resolved in Slice 4)
  -> emit SystemUpdateRequest
       (structured record — not a file edit, physics mutation, Coding Agent
        call, or activation)
```

The output of this slice is a fully structured `SystemUpdateRequest`. No
downstream mutation, build, or activation follows automatically from
classification alone. Every downstream action requires its own governance
step.

---

## Classification Types

The following canonical classification values are established for the initial
supported request surface. Each type carries its expected later routing
implication so downstream slices have an agreed path to implement against.

---

### `physics_edit`

A request to change non-executable model or domain physics: policy
thresholds, standing orders, invariants, escalation rules, or related
rule/specification material.

**Expected later routing:**

```text
SystemUpdateRequest (classified_type: physics_edit)
  -> PhysicsEditProposal path
  -> schema validation + invariant/conflict validation  (Slice 6+)
  -> authority review                                   (Slice 4)
  -> domain-physics update + hash commitment
```

The Coding Agent is not involved in ordinary physics edits.

---

### `domain_lib_or_spec_update`

A request to update pack or module `lib/` material, reference
specifications, support knowledge, or domain/library documentation.

> **Note:** Older documentation may still refer to this surface as
> `domain-lib`. Both terms refer to the same concept until the library
> structure refactor slice lands. The canonical enum value for this
> classification is `domain_lib_or_spec_update`.

**Expected later routing:**

```text
SystemUpdateRequest (classified_type: domain_lib_or_spec_update)
  -> DomainLibraryUpdateProposal path
  -> authority review  (Slice 4)
  -> lib/ artifact update
```

---

### `tooling_build_request`

A request to build or modify executable or supporting tooling that does not
fit a more specific surface category (API endpoint, slash command, or module
workflow).

**Expected later routing:**

```text
SystemUpdateRequest (classified_type: tooling_build_request)
  -> ToolingBuildRequest path
  -> System Pack scoping                (Slice 5)
  -> Coding Agent build workflow        (later Coding Agent slices)
```

---

### `new_api_endpoint`

A request to create a new API endpoint or handler surface.

**Expected later routing:**

```text
SystemUpdateRequest (classified_type: new_api_endpoint)
  -> ToolingBuildRequest with API endpoint template requirements
  -> System Pack scoping + Template Pack selection
  -> Coding Agent build workflow
```

---

### `new_slash_command`

A request to create a new slash command or command-like interaction surface.

**Expected later routing:**

```text
SystemUpdateRequest (classified_type: new_slash_command)
  -> ToolingBuildRequest with slash command template requirements
  -> System Pack scoping + Template Pack selection
  -> Coding Agent build workflow
```

---

### `new_module_workflow`

A request to create or modify a module workflow.

**Expected later routing:**

```text
SystemUpdateRequest (classified_type: new_module_workflow)
  -> ToolingBuildRequest    (if the scope is executable)
       or
     DomainLibraryUpdateProposal  (if the scope is spec-only)
  -> resolved by System Pack authority gate  (Slice 4)
```

---

### `registration_request`

A request to register a staged and authorised artifact into the framework's
active surface.

**Expected later routing:**

```text
SystemUpdateRequest (classified_type: registration_request)
  -> RegistrationRequest path
  -> System Pack authority gate  (Slice 4)
  -> registration + activation lifecycle  (later registration/activation slices)
```

---

### `unsupported_or_needs_developer`

A request that is ambiguous, unsafe, under-specified, outside the framework
boundary, or requires developer review before it can become a more specific
request type.

**Expected later routing:**

```text
SystemUpdateRequest (classified_type: unsupported_or_needs_developer)
  -> escalation / clarification path
  -> developer review
  -> requester prompted for more information (clarification_questions)
```

This type is the safe fallback for any request that cannot be confidently
classified. Classification must never guess an executable action when the
request is ambiguous or unsafe. Ambiguous input becomes
`unsupported_or_needs_developer`, not a guessed action.

---

## New/Changed Contracts

### `ClassificationRecord`

The `ClassificationRecord` is the structured output of the intake and
classification step. It is embedded in (or referenced by) the
`SystemUpdateRequest` that Slice 3 emits.

**Expected fields / concepts:**

| Field | Description |
|-------|-------------|
| `classification_id` | Unique identifier for this classification record |
| `request_id` | Foreign key to the parent `SystemUpdateRequest` |
| `classified_type` | One of the eight canonical values defined above |
| `confidence` | Classifier's confidence in the assigned type (e.g. `high`, `medium`, `low`) |
| `reasoning_summary` | Concise, audit-safe explanation of why this type was chosen — not raw chain-of-thought |
| `requested_scope` | Pack, module, or surface the requester identified or that was inferred |
| `requires_clarification` | Boolean; `true` when the request is under-specified or ambiguous |
| `clarification_questions` | Ordered list of questions to ask the requester if `requires_clarification` is `true` |
| `proposed_next_record_type` | The downstream record type that System Pack should create next (e.g. `PhysicsEditProposal`, `ToolingBuildRequest`) |
| `authority_context_placeholder` | Requester identity captured at classification time; authority level resolved by Slice 4, not Slice 3 |
| `created_at` | ISO-8601 timestamp of when classification completed |

> **Audit safety:** `reasoning_summary` must be a concise, human-readable
> explanation suitable for audit records. Private chain-of-thought must not
> be exposed in this field.

Field names are indicative. Exact implementation names are confirmed when the
schema convention for this repository is established in a later slice.

### `SystemUpdateRequest` (updated understanding)

This slice builds directly on the `SystemUpdateRequest` vocabulary
established in [Slice 2](02-system-update-vocabulary.md#systemupdaterequest).
The intake and classification step is what produces the initial
`SystemUpdateRequest` from a raw natural-language input. No prior slice
defined a concrete producer of this record; Slice 3 fills that gap.

---

## Files Likely Touched

```
docs/
  roadmap/
    README.md                                        ← UPDATED (Slice 3 row added)
    slices/
      03-request-intake-and-classification.md        ← NEW (this file)
  MANIFEST.yaml                                      ← UPDATED (new entry added)
```

---

## Acceptance Criteria

- [ ] `docs/roadmap/slices/03-request-intake-and-classification.md` exists
      with all required sections.
- [ ] The intake flow from natural-language request to structured
      `SystemUpdateRequest` is documented end-to-end.
- [ ] The classification output is explicitly a structured record, not a
      direct mutation, build action, or activation.
- [ ] All eight canonical classification types are documented:
  - `physics_edit`
  - `domain_lib_or_spec_update`
  - `tooling_build_request`
  - `new_api_endpoint`
  - `new_slash_command`
  - `new_module_workflow`
  - `registration_request`
  - `unsupported_or_needs_developer`
- [ ] Each classification type documents its expected later routing
      implication.
- [ ] Documentation states that classification does not grant authority and
      does not activate anything.
- [ ] Documentation states that ambiguous, unsafe, or under-specified
      requests must route to `unsupported_or_needs_developer`, not guessed
      actions.
- [ ] Documentation preserves the invariant that the System Pack is the only
      ingress to the Coding Agent.
- [ ] `reasoning_summary` is documented as audit-safe; private
      chain-of-thought is not exposed.
- [ ] `docs/roadmap/README.md` includes a Slice 3 row in the Slice Index
      table.
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

No automated markdown linting is currently configured in this repository. If
a markdown linter is added in a future slice, it should be applied to these
files at that time.

---

## Ledger/Governance Impact

This slice introduces no ledger writes and no state machine transitions. It
is purely additive documentation.

The governance impact is **classification contract lock-in**: future
implementation slices, model-pack authors, and contributors now have a single
authoritative reference for the eight canonical classification types and the
intake flow that produces a `SystemUpdateRequest`. Using these classifications
consistently across slices prevents ambiguity about which downstream path a
classified request should follow.

---

## Governance and Safety Invariants

The following invariants must be preserved by any implementation of this
slice and all subsequent slices that touch classification:

```text
1. Natural-language intake does not directly mutate system state.
2. Classification does not grant authority.
3. Classification does not activate anything.
4. The Coding Agent is never invoked directly by intake or classification.
5. The System Pack remains the sole ingress to Coding Agent workflows.
6. Ambiguous or unsafe requests become unsupported_or_needs_developer,
   not guessed actions.
7. Mechanical correctness / automated testing does not equal governance
   approval.
```

These invariants are inherited from the framework foundational principles
documented in [Slice 1](01-framework-boundary.md) and
[Slice 2](02-system-update-vocabulary.md) and remain binding for all
subsequent slices.

---

## Follow-Up Slices

| Slice | Anticipated Title |
|-------|-------------------|
| 04 | System Pack Authority Gate — authority validation, scope resolution, requester role checks |
| 05 | System Pack as Sole Coding Agent Ingress — enforce single-ingress invariant at the implementation level |
| 06 | Physics Edit Proposal Flow — natural-language-to-`PhysicsEditProposal` conversion |
| 07 | Physics Proposal Schema and Patch Contract — JSON Patch/structured proposal schema, invariant/conflict validation |
