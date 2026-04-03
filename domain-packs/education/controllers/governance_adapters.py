"""Education governance adapters — state builder and domain step for non-learning roles.

Governance roles (domain_authority, teacher, teaching_assistant, guardian) use
these adapters instead of the learning-specific ZPD/fluency monitors.  The
pattern mirrors the system domain's ``build_system_state`` /
``system_domain_step`` in domain-packs/system/controllers/runtime_adapters.py.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("lumina-education-governance-adapter")

# query_type → resolved action name for governance roles.
_QUERY_TYPE_ACTION_MAP: dict[str, str] = {
    "admin_command": "governance_command",
    "status_query": "governance_status",
    "progress_review": "governance_progress",
    "module_management": "governance_management",
    "escalation_review": "governance_escalation",
    "out_of_domain": "out_of_domain",
    "general": "governance_general",
}

# query_types routed to structured command dispatch.
_COMMAND_DISPATCH_TYPES: frozenset[str] = frozenset(
    {"admin_command", "module_management"}
)


def build_governance_state(
    entity_profile: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Build session state for a governance role.

    No learning curves, affect tracking, or ZPD — just a minimal state dict
    with turn counter and operator identity.
    """
    return {
        "turn_count": 0,
        "operator_id": entity_profile.get("operator_id", entity_profile.get("subject_id", "")),
        "domain_id": entity_profile.get("domain_id", ""),
        "role": entity_profile.get("role", ""),
    }


def governance_domain_step(
    state: dict[str, Any],
    task_spec: dict[str, Any],
    evidence: dict[str, Any],
    params: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Advance governance session state by one turn.

    Maps the classified query_type to a concrete action code so the
    orchestrator produces a governance prompt template instead of falling
    back to ``task_presentation``.
    """
    new_state = dict(state)
    new_state["turn_count"] = int(new_state.get("turn_count", 0)) + 1

    query_type: str = evidence.get("query_type") or "general"
    has_command_dispatch = bool(evidence.get("command_dispatch"))

    if has_command_dispatch:
        resolved_action = "governance_command"
    else:
        resolved_action = _QUERY_TYPE_ACTION_MAP.get(query_type, "governance_general")

    action: dict[str, Any] = {
        "tier": "ok",
        "action": resolved_action,
        "query_type": query_type,
        "target_component": evidence.get("target_component"),
        "command_dispatch": evidence.get("command_dispatch"),
    }
    return new_state, action
