# Section 7 — Concepts

**Version:** 1.0.0  
**Status:** Active  
**Last updated:** 2026-03-12  

---

Architectural principles, design frameworks, and system philosophy.

| Concept | Description |
|---------|-------------|
| [principles-v1](../../specs/principles-v1.md) | Non-negotiable system principles |
| [dsa-framework-v1](../../specs/dsa-framework-v1.md) | Diagnosis → Selection → Action framework |
| [rag-contracts](../../retrieval/rag-contracts.md) | RAG retrieval contract model |
| [domain-adapter-pattern](domain-adapter-pattern.md) | How domain packs extend the engine: NLP pre-processing, signal synthesis, engine contract fields, three-layer distinction (tool-adapters / domain-lib / runtime-adapter) |
| [nlp-semantic-router](nlp-semantic-router.md) | Two-tier NLP architecture: Tier 1 system-level domain classification (`classify_domain`), Tier 2 domain NLP pre-interpreter (`_nlp_anchors`), three-stage input pipeline, glossary intercept, routing surface evolution |
| [prompt-packet-assembly](prompt-packet-assembly.md) | How prompt contracts are assembled from layered components: layer reference table, input sources and telemetry, domain library tools, what the LLM sees vs. what is hidden |
| [zero-trust-architecture](zero-trust-architecture.md) | Zero-trust posture across all Lumina layers: per-layer trust enforcement matrix, NIST SP 800-207 tenet mapping, OWASP Top 10 mapping, operational implications (fail-closed defaults, escalation, pseudonymity) |

These documents define the foundational design philosophy of Project Lumina. All implementation decisions trace back to these concepts.
