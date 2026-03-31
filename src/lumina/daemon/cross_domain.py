"""
cross_domain.py — Cross-domain synthesis analysis functions.

Pure, domain-agnostic functions that compare glossary structure and
invariant patterns across domain physics documents.  Used by the
``cross_domain_synthesis`` daemon task to identify structural
similarities between opt-in domain pairs.

Design invariant: zero domain-specific names may appear in this module.
All analysis operates on generic glossary_entry and invariant dicts.
"""

from __future__ import annotations

import itertools
import logging
import re
from typing import Any

log = logging.getLogger("lumina-daemon")


# ── Opt-in helpers ──────────────────────────────────────────────

def get_opt_in_config(domain_physics: dict[str, Any]) -> dict[str, Any] | None:
    """Return the cross_domain_synthesis config block, or None if disabled."""
    cfg = domain_physics.get("cross_domain_synthesis")
    if cfg is None or not cfg.get("enabled", False):
        return None
    return cfg


def is_mutual_peer(
    domain_a_id: str,
    domain_a_physics: dict[str, Any],
    domain_b_id: str,
    domain_b_physics: dict[str, Any],
) -> bool:
    """Return True iff both domains opt in *and* list each other as peers."""
    cfg_a = get_opt_in_config(domain_a_physics)
    cfg_b = get_opt_in_config(domain_b_physics)
    if cfg_a is None or cfg_b is None:
        return False
    peers_a = cfg_a.get("peer_domains") or []
    peers_b = cfg_b.get("peer_domains") or []
    return domain_b_id in peers_a and domain_a_id in peers_b


def filter_mutual_pairs(
    domains: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return all mutually opted-in domain pairs from *domains*.

    Each element in *domains* must have at least ``domain_id`` and
    ``physics`` keys.
    """
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for a, b in itertools.combinations(domains, 2):
        if is_mutual_peer(
            a["domain_id"], a["physics"],
            b["domain_id"], b["physics"],
        ):
            pairs.append((a, b))
    return pairs


# ── Pass 1: Glossary structural comparison ──────────────────────

def _normalise_term(term: str) -> str:
    """Lowercase, strip whitespace, collapse internal spacing."""
    return re.sub(r"\s+", " ", term.strip().lower())


def _extract_term_set(glossary: list[dict[str, Any]]) -> set[str]:
    """Extract all canonical terms and aliases from a glossary."""
    terms: set[str] = set()
    for entry in glossary:
        canonical = _normalise_term(entry.get("term", ""))
        if canonical:
            terms.add(canonical)
        for alias in entry.get("aliases") or []:
            normalised = _normalise_term(alias)
            if normalised:
                terms.add(normalised)
    return terms


def _extract_related_terms(glossary: list[dict[str, Any]]) -> set[str]:
    """Extract all related_terms references from a glossary."""
    related: set[str] = set()
    for entry in glossary:
        for rt in entry.get("related_terms") or []:
            normalised = _normalise_term(rt)
            if normalised:
                related.add(normalised)
    return related


def compare_glossaries(
    glossary_a: list[dict[str, Any]],
    glossary_b: list[dict[str, Any]],
    min_overlap: float = 0.15,
) -> dict[str, Any]:
    """Compare two glossary arrays for structural term overlap.

    Returns a dict with:
    - shared_terms: set of overlapping terms (canonical + aliases)
    - shared_related: set of overlapping related_terms references
    - score: shared_terms count / min(len(terms_a), len(terms_b))
    - passes_threshold: score >= min_overlap
    """
    terms_a = _extract_term_set(glossary_a)
    terms_b = _extract_term_set(glossary_b)

    shared_terms = terms_a & terms_b

    related_a = _extract_related_terms(glossary_a)
    related_b = _extract_related_terms(glossary_b)
    shared_related = related_a & related_b

    denominator = min(len(terms_a), len(terms_b)) if terms_a and terms_b else 0
    score = len(shared_terms) / denominator if denominator > 0 else 0.0

    return {
        "shared_terms": sorted(shared_terms),
        "shared_related": sorted(shared_related),
        "terms_a_count": len(terms_a),
        "terms_b_count": len(terms_b),
        "score": round(score, 4),
        "passes_threshold": score >= min_overlap,
    }


# ── Pass 2: Invariant structure comparison ──────────────────────

def _invariant_signature(invariant: dict[str, Any]) -> dict[str, Any]:
    """Extract a domain-agnostic structural signature from an invariant.

    The signature captures the *shape* of the invariant rather than its
    domain-specific semantics:
    - severity level
    - whether it has a check expression
    - whether it delegates to a subsystem (handled_by present)
    - whether it chains to a standing order
    - whether it emits a signal type
    """
    return {
        "severity": invariant.get("severity", ""),
        "has_check": bool(invariant.get("check")),
        "has_handled_by": bool(invariant.get("handled_by")),
        "has_standing_order": bool(invariant.get("standing_order_on_violation")),
        "has_signal_type": bool(invariant.get("signal_type")),
    }


def compare_invariant_structures(
    invariants_a: list[dict[str, Any]],
    invariants_b: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare invariant structural patterns across two domains.

    Looks for *invariant homomorphisms* — invariants that share the same
    structural role (severity, delegation style, chaining pattern)
    regardless of their domain-specific semantics.

    Returns a dict with:
    - matched_pairs: list of (inv_a_id, inv_b_id, shared_signature) triples
    - score: matched_pairs count / min(len_a, len_b)
    """
    sigs_a = [
        (inv.get("id", f"inv_a_{i}"), _invariant_signature(inv))
        for i, inv in enumerate(invariants_a)
    ]
    sigs_b = [
        (inv.get("id", f"inv_b_{i}"), _invariant_signature(inv))
        for i, inv in enumerate(invariants_b)
    ]

    matched_pairs: list[dict[str, Any]] = []
    used_b: set[str] = set()

    for a_id, a_sig in sigs_a:
        for b_id, b_sig in sigs_b:
            if b_id in used_b:
                continue
            if a_sig == b_sig:
                matched_pairs.append({
                    "invariant_a_id": a_id,
                    "invariant_b_id": b_id,
                    "shared_signature": a_sig,
                })
                used_b.add(b_id)
                break

    denominator = min(len(sigs_a), len(sigs_b)) if sigs_a and sigs_b else 0
    score = len(matched_pairs) / denominator if denominator > 0 else 0.0

    return {
        "matched_pairs": matched_pairs,
        "invariants_a_count": len(sigs_a),
        "invariants_b_count": len(sigs_b),
        "score": round(score, 4),
    }


# ── Full two-pass analysis ──────────────────────────────────────

def find_synthesis_candidates(
    domains: list[dict[str, Any]],
    glossary_min_overlap: float = 0.15,
) -> list[dict[str, Any]]:
    """Run the full two-pass cross-domain analysis.

    Parameters
    ----------
    domains : list[dict]
        Each element must have ``domain_id`` (str) and ``physics`` (dict)
        keys.  The physics dict must be a valid domain-physics document.
    glossary_min_overlap : float
        Minimum glossary overlap score to proceed to Pass 2.

    Returns
    -------
    list[dict]
        One entry per domain pair that produced matches.  Each dict contains:
        - domain_a_id, domain_b_id
        - glossary_result (Pass 1 output)
        - invariant_result (Pass 2 output, or None if Pass 1 didn't pass)
        - is_candidate: True if at least one pass found meaningful overlap
    """
    pairs = filter_mutual_pairs(domains)
    candidates: list[dict[str, Any]] = []

    for dom_a, dom_b in pairs:
        a_id = dom_a["domain_id"]
        b_id = dom_b["domain_id"]
        a_physics = dom_a["physics"]
        b_physics = dom_b["physics"]

        cfg_a = get_opt_in_config(a_physics) or {}
        cfg_b = get_opt_in_config(b_physics) or {}

        # Pass 1: Glossary structural comparison
        glossary_result: dict[str, Any] | None = None
        if cfg_a.get("share_glossary", True) and cfg_b.get("share_glossary", True):
            glossary_a = a_physics.get("glossary") or []
            glossary_b = b_physics.get("glossary") or []
            if glossary_a and glossary_b:
                glossary_result = compare_glossaries(
                    glossary_a, glossary_b, min_overlap=glossary_min_overlap,
                )

        # Pass 2: Invariant structure comparison (runs if glossary passed OR
        # if glossary comparison was skipped/inapplicable)
        invariant_result: dict[str, Any] | None = None
        run_pass_2 = (
            (glossary_result is not None and glossary_result["passes_threshold"])
            or glossary_result is None  # no glossary data → still check invariants
        )
        if run_pass_2 and cfg_a.get("share_invariant_structure", True) and cfg_b.get("share_invariant_structure", True):
            invariants_a = a_physics.get("invariants") or []
            invariants_b = b_physics.get("invariants") or []
            if invariants_a and invariants_b:
                invariant_result = compare_invariant_structures(
                    invariants_a, invariants_b,
                )

        is_candidate = (
            (glossary_result is not None and glossary_result["passes_threshold"])
            or (invariant_result is not None and invariant_result["score"] > 0)
        )

        candidates.append({
            "domain_a_id": a_id,
            "domain_b_id": b_id,
            "glossary_result": glossary_result,
            "invariant_result": invariant_result,
            "is_candidate": is_candidate,
        })

    return candidates
