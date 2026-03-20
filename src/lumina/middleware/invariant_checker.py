"""Domain-pack-driven invariant check evaluator.

Extracted from ``ppa_orchestrator.py`` to serve as the standalone,
domain-agnostic invariant evaluation engine used by the Inspection
Middleware pipeline.

The evaluator reads ``check`` predicate expressions declared in each
domain-pack invariant definition and evaluates them against a flat
evidence dict.

Supported expression forms
--------------------------
``<field>``                 – truthy check on ``evidence[field]``
``<field> == <literal>``    – equality   (``[]`` / ``true`` / ``false`` / number / string)
``<field> != <literal>``    – inequality
``<field> >= <number>``     – numeric GTE (also ``>``, ``<``, ``<=``)

The right-hand side may also be a field reference resolved from the
evidence dict (e.g. ``step_count >= min_steps``).
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("lumina.middleware.invariant_checker")


# ─────────────────────────────────────────────────────────────
# Literal parser
# ─────────────────────────────────────────────────────────────

def parse_check_literal(raw: str) -> Any:
    """Parse the right-hand side literal of a check expression.

    Handles ``[]``, ``true``/``false``, integers, floats, and falls
    back to a plain string for anything else.
    """
    raw = raw.strip()
    if raw == "[]":
        return []
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    log.debug("Check literal %r treated as plain string", raw)
    return raw


# ─────────────────────────────────────────────────────────────
# Single-expression evaluator
# ─────────────────────────────────────────────────────────────

def evaluate_check_expr(check_expr: str, evidence: dict[str, Any]) -> bool | None:
    """Evaluate a domain-pack ``check`` expression against an evidence dict.

    Returns ``True`` if the invariant passes, ``False`` if it fails, or
    ``None`` when the referenced evidence field is absent (caller should
    skip the invariant rather than false-positive).
    """
    tokens = check_expr.strip().split(None, 2)

    if len(tokens) == 1:
        field = tokens[0]
        if field not in evidence:
            return None
        if evidence[field] is None:
            return None
        return bool(evidence[field])

    if len(tokens) == 3:
        field, op, raw_val = tokens
        if field not in evidence:
            return None
        ev_val = evidence[field]
        rhs = parse_check_literal(raw_val)
        if isinstance(rhs, str):
            if raw_val not in evidence:
                return None
            rhs = evidence[raw_val]
        if op == "==":
            return ev_val == rhs
        if op == "!=":
            return ev_val != rhs
        if op == ">=":
            return ev_val >= rhs
        if op == "<=":
            return ev_val <= rhs
        if op == ">":
            return ev_val > rhs
        if op == "<":
            return ev_val < rhs
        log.warning("Unknown operator %r in check expression %r", op, check_expr)
        return None

    # Two-token expression (malformed) — return None to skip
    return None


# ─────────────────────────────────────────────────────────────
# Batch invariant evaluator
# ─────────────────────────────────────────────────────────────

def evaluate_invariants(
    invariants: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate all domain-pack invariants against structured evidence.

    Invariants marked with ``"handled_by": "<subsystem>"`` are skipped
    and delegated to the registered domain lib.

    Returns a list of result dicts::

        {
            "id": str,
            "severity": "critical" | "warning",
            "passed": bool,
            "standing_order_on_violation": str | None,
            "signal_type": str | None,
        }

    Invariants whose ``check`` field is absent or whose evidence field
    is missing from the supplied dict are silently skipped (no false
    negatives from missing data).
    """
    results: list[dict[str, Any]] = []
    for inv in invariants:
        inv_id: str = inv["id"]

        if inv.get("handled_by"):
            continue

        check_expr: str | None = inv.get("check")
        if not check_expr:
            log.debug("No check expression for invariant %r — skipping", inv_id)
            continue

        try:
            result = evaluate_check_expr(check_expr, evidence)
        except Exception as exc:
            log.warning("Invariant %r check raised %r — skipping", inv_id, exc)
            continue

        if result is None:
            log.debug(
                "Missing evidence for invariant %r (check=%r) — skipping",
                inv_id,
                check_expr,
            )
            continue

        results.append(
            {
                "id": inv_id,
                "severity": inv.get("severity", "warning"),
                "passed": result,
                "standing_order_on_violation": inv.get(
                    "standing_order_on_violation"
                ),
                "signal_type": inv.get("signal_type"),
            }
        )
    return results
