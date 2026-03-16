from __future__ import annotations

import json
from typing import Any, Callable


def build_system_state(
    entity_profile: dict[str, Any],
    runtime_ctx: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the initial (or restored) session state for a system-domain session.

    The system domain does not track learning curves, affect, or ZPD — the state
    is intentionally minimal: just a turn counter and the operator's profile fields.
    """
    prior = dict(session_state or {})
    return {
        "turn_count": int(prior.get("turn_count", 0)),
        "operator_id": entity_profile.get("operator_id", ""),
        "domain_id": entity_profile.get("domain_id", "domain/sys/system-core/v1"),
    }


def system_domain_step(
    state: dict[str, Any],
    task_spec: dict[str, Any],
    evidence: dict[str, Any],
    params: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Advance the system-domain session state by one turn.

    No domain-specific model updates are needed — the system domain is
    conversational only.  Returns the incremented state and a neutral action dict.
    """
    new_state = dict(state)
    new_state["turn_count"] = int(new_state.get("turn_count", 0)) + 1
    action: dict[str, Any] = {
        "tier": "ok",
        "action": None,
        "query_type": evidence.get("query_type", "general"),
        "target_component": evidence.get("target_component"),
    }
    return new_state, action


def _strip_markdown_fences(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[: cleaned.rfind("```")]
    return cleaned.strip()


def interpret_turn_input(
    call_llm: Callable[[str, str, str | None], str],
    input_text: str,
    task_context: dict[str, Any],
    prompt_text: str,
    default_fields: dict[str, Any] | None = None,
    tool_fns: dict[str, Callable[..., Any]] | None = None,
) -> dict[str, Any]:
    """Classify the operator's message into a structured evidence dict."""
    raw_response = call_llm(
        system=prompt_text,
        user=f"Operator message: {input_text}",
        model=None,
    )

    try:
        evidence = json.loads(_strip_markdown_fences(raw_response))
    except (json.JSONDecodeError, IndexError):
        evidence = {}

    defaults: dict[str, Any] = dict(default_fields or {}) or {
        "query_type": "general",
        "target_component": None,
        "off_task_ratio": 0.0,
        "response_latency_sec": 5.0,
    }
    for key, default_val in defaults.items():
        if key not in evidence or evidence[key] is None:
            evidence[key] = default_val

    return evidence
