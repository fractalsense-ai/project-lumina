# Novel Synthesis Framework

**Version:** 1.0.0  
**Status:** Active  
**Last updated:** 2026-03-13  

---

This document defines how Project Lumina detects, verifies, and records novel synthesis events — moments when the LLM reasoning engine identifies a non-obvious connection or approach that does not match any known pattern in the active domain physics. The framework spans two modular boundaries (domain and system) and provides the telemetry foundation for cross-domain model performance benchmarking.

---

## A. What Is Novel Synthesis?

A **novel synthesis** occurs when the LLM produces a response that the domain's evidence extractors cannot classify using existing rules. In an algebra domain this might be an unrecognized solution method; in an agriculture domain it might be a novel pest-management correlation.

The core problem: LLMs generate enormous volumes of output. Most of it matches known patterns and can be handled deterministically. The rare signal — a genuinely new and useful connection — is buried in noise. Without a structured framework, innovations go unrecorded and the system cannot distinguish between a model that parrots known answers and one that generates genuine insight.

Novel synthesis tracking solves this by:

1. **Isolating the signal from noise** — only flagged, non-obvious connections enter the verification pipeline.
2. **Requiring human confirmation** — the system never self-validates innovation; a domain authority must turn the second key.
3. **Recording lean metadata** — the system CTL stores only the audit trail (domain, model, timestamp, verdict), not the raw content.
4. **Enabling model benchmarking** — by correlating novel synthesis rates with model identity, the system builds a performance heatmap across domains.

---

## B. The Two-Key Verification Gate

Novel synthesis uses a **two-key gate** — two independent confirmations before the system records an event as validated innovation.

### Key 1 — LLM / Domain Adapter

The first key turns when the domain's evidence extraction pipeline cannot classify the LLM's response using existing rules. This is expressed in the domain physics as a warning invariant with a `signal_type`:

```yaml
# domain-packs/<domain>/modules/<module>/domain-physics.yaml
invariants:
  - id: standard_method_preferred
    severity: warning
    check: "method_recognized"
    standing_order_on_violation: request_method_justification
    signal_type: NOVEL_PATTERN
```

When `method_recognized` evaluates to `false`, the invariant fires. The orchestrator:

1. Applies the standing order (`request_method_justification`) — asking the subject to explain their reasoning.
2. Propagates the `signal_type` into the TraceEvent metadata as `novel_synthesis_signal`.
3. If the standing order exhausts without resolution, creates an EscalationRecord with `trigger_type: novel_synthesis_review`.

Key 1 is entirely domain-owned. The engine does not hardcode signal types — it propagates whatever `signal_type` string the domain physics defined on the failing invariant.

### Key 2 — Domain Authority (Human-in-the-Loop)

The second key turns when the Domain Authority reviews the escalation and issues a resolution:

| Verdict | CommitmentRecord `commitment_type` | Effect |
|---------|--------------------------------------|--------|
| Accepted | `novel_synthesis_verified` | Innovation recorded; domain physics may be updated to recognize the pattern in future |
| Rejected | `novel_synthesis_rejected` | Flagged as false positive; model may be flagged for reliability concerns |

The system does **not** learn the new concept until Key 2 turns. This prevents hallucinated "innovations" from polluting the domain knowledge base.

### Lifecycle Diagram

```
  ┌─────────────────────────────────────────────────────────────┐
  │                    DOMAIN BOUNDARY                          │
  │                                                             │
  │  Evidence Extraction                                        │
  │       │                                                     │
  │       ▼                                                     │
  │  method_recognized == false                                 │
  │       │                                                     │
  │       ▼                                                     │
  │  Invariant fires ──► Standing Order                         │
  │  signal_type:          (request_method_justification)       │
  │  NOVEL_PATTERN              │                               │
  │       │                     ▼                               │
  │       │              Exhausted? ──yes──► EscalationRecord   │
  │       │                                  trigger_type:      │
  │       │                                  novel_synthesis_   │
  │       │                                  review             │
  │       │                                      │              │
  │       │                                      ▼              │
  │       │                              Domain Authority       │
  │       │                              reviews (Key 2)        │
  │       │                                      │              │
  │       │                     ┌────────────────┼──────────┐   │
  │       │                     ▼                ▼          │   │
  │       │              VERIFIED          REJECTED         │   │
  │       │              CommitmentRecord   CommitmentRecord │   │
  └───────│─────────────────────│────────────────│──────────┘   │
          │                     │                │              │
  ┌───────│─────────────────────│────────────────│──────────┐   │
  │       │    SYSTEM BOUNDARY  │                │          │   │
  │       ▼                     ▼                ▼          │   │
  │  TraceEvent            System CTL records verdict       │   │
  │  metadata:             + model_id + model_version       │   │
  │    model_id            + domain_pack_id                 │   │
  │    model_version                                        │   │
  │    novel_synthesis_signal                               │   │
  │                                                         │   │
  └─────────────────────────────────────────────────────────┘   │
```

---

## C. System-Level Telemetry

The system boundary tracks model identity without inspecting domain logic. Every TraceEvent's `metadata` carries:

| Key | Source | Purpose |
|-----|--------|---------|
| `model_id` | Per-request (`ChatRequest.model_id`) | LLM identifier (e.g. `claude-sonnet-4-20250514`) |
| `model_version` | Per-request (`ChatRequest.model_version`) | Model revision/version string |
| `novel_synthesis_signal` | Orchestrator (from failing invariant `signal_type`) | Presence indicates Key 1 has turned |

The system CTL stores only the **metadata** for the audit — not the raw synthesis content. This creates a reproducible "Map of Innovation" without bloating the system ledger:

- **Tag:** `NOVEL_SYNTHESIS` (the `novel_synthesis_signal` value in TraceEvent metadata)
- **Metadata:** `domain_pack_id`, `model_id`, `model_version`, `timestamp_utc`
- **Resolution:** `novel_synthesis_verified` or `novel_synthesis_rejected` CommitmentRecord

---

## D. Compute Efficiency Argument

The novel synthesis framework interacts with two existing efficiency mechanisms:

### Stage 2 Intercept — Glossary Lookups

When a user asks "what is a variable?" in the algebra domain, the glossary intercept pipeline (`_detect_glossary_query` in `src/lumina/api/server.py`) returns the deterministic definition immediately. This saves 100% of LLM compute for known terms — the LLM is never invoked.

Novel synthesis, by definition, is what the glossary **cannot** handle. It is the complement of deterministic lookup: when no known pattern matches, the system falls through to the LLM for creative reasoning.

### Grounding Anchors

By providing the domain's "truth" up front via the prompt contract — invariants, standing orders, glossary terms, and domain physics — the system enables:

- **Smaller, cheaper models** to explain what larger models would have to discover from scratch.
- **Novel synthesis tracking** to identify where a model adds genuine value beyond the grounding material.

The efficiency argument: if Model A produces the same novel synthesis rate as Model B but costs 10x more, the grounding anchors have made the cheaper model equally capable for that domain. The telemetry makes this comparison possible.

---

## E. Model Performance Benchmarking

Novel synthesis metadata enables three forms of model intelligence:

### 1. LLM Performance Heatmap

By aggregating `novel_synthesis_signal` events grouped by `model_id` x `domain_pack_id`, the system builds a performance matrix:

```
                    Education    Agriculture    Lab-Science
claude-sonnet-4       ██████       ███            █████████
gpt-5                 ████         ████████       ██████
gemini-2-ultra        ████████     █████          ████

█ = verified novel synthesis events per 1000 turns
```

If a spike appears when switching a domain from one model to another, the system has discovered which model has better "latent correlation" for that subject matter.

**The "Physics" of the Model:** Some models are better at creative synthesis (connecting disparate dots), while others are better at deterministic logic (following the rules). The heatmap makes this visible at the domain level.

### 2. Domain-to-Model Optimization

The telemetry enables future **dynamic routing**: the system examines historical novel synthesis rates and routes domain packets to the model with the best track record for that domain. This is a Darwinian selection process — models that produce verified insights survive; those that produce noise are deprioritized.

> **Note:** Automatic model routing is a planned future capability. The current slice provides the telemetry foundation only.

### 3. Model Drift Detection

The two-key gate protects against **model collapse**. If a new model version starts hallucinating "novel" ideas that Key 2 (the domain authority) keeps rejecting, the rejection rate spikes. The system can:

- Flag the model version as unreliable for that domain.
- Alert the Meta Authority to consider rolling back to a known stable version.
- Provide evidence for the rollback decision via the CTL audit trail.

The signal: if the `novel_synthesis_rejected` rate increases significantly after a model update, the provider may have degraded the model's reasoning capabilities. The system catches this immediately because the system-level ledger shows a dip in verified innovation alongside the model version change.

---

## F. Domain Pack Integration

To enable novel synthesis tracking in a domain pack, a domain author adds three elements to the domain physics:

### 1. Warning Invariant with `signal_type`

```yaml
invariants:
  - id: standard_method_preferred
    description: >
      Non-standard approaches are acceptable but flagged for review.
    severity: warning
    check: "method_recognized"
    standing_order_on_violation: request_method_justification
    signal_type: NOVEL_PATTERN
```

The `signal_type` value is a free-form string. The engine propagates it verbatim — the domain owns the vocabulary.

### 2. Standing Order

```yaml
standing_orders:
  - id: request_method_justification
    action: request_method_justification
    trigger_condition: standard_method_preferred
    max_attempts: 1
    escalation_on_exhaust: false
    description: >
      Acknowledge the non-standard approach and ask the subject
      to explain their reasoning. Flag for Domain Authority review.
```

### 3. Escalation Trigger

```yaml
escalation_triggers:
  - id: novel_pattern_review
    condition: >
      standard_method_preferred invariant fired and the method
      is unrecognized after justification request.
    target_role: teacher
    sla_minutes: 120
```

No changes to `src/lumina/` are required. The engine's generic `signal_type` propagation handles any domain that wires these fields.

---

## SEE ALSO

- [`domain-adapter-pattern(7)`](domain-adapter-pattern.md) — Engine contract fields, three-layer distinction, Phase A/B lifecycle
- [`nlp-semantic-router(7)`](nlp-semantic-router.md) — Two-tier NLP architecture, glossary intercept
- [`dsa-framework-v1`](../../specs/dsa-framework-v1.md) — D.S.A. orchestrator specification
- [`trace-event-schema`](../../ledger/trace-event-schema.json) — TraceEvent schema with `novel_synthesis_flagged` event type and `model_id`/`model_version` metadata keys
- [`commitment-record-schema`](../../ledger/commitment-record-schema.json) — CommitmentRecord with `novel_synthesis_verified` / `novel_synthesis_rejected` types
- [`escalation-record-schema`](../../ledger/escalation-record-schema.json) — EscalationRecord with `novel_synthesis_review` trigger type
