"""Structured content builders for chat action cards.

Factory functions that populate ``ChatResponse.structured_content``
(historically always ``None``).  Two card types are supported:

- **escalation** — surfaces an EscalationRecord to the session
  supervisor (teacher) or domain authority so they can approve / reject /
  defer directly in the chat interface.
- **command_proposal** — surfaces a staged HITL admin command so the
  authority can accept / reject / modify it inline.
"""

from __future__ import annotations

from typing import Any


# ── Action definitions ────────────────────────────────────────

_ESCALATION_ACTIONS: list[dict[str, str]] = [
    {"id": "approve", "label": "Approve", "style": "primary"},
    {"id": "reject", "label": "Reject", "style": "destructive"},
    {"id": "defer", "label": "Defer", "style": "ghost"},
]

_COMMAND_ACTIONS: list[dict[str, str]] = [
    {"id": "accept", "label": "Accept", "style": "primary"},
    {"id": "reject", "label": "Reject", "style": "destructive"},
    {"id": "modify", "label": "Modify", "style": "outline"},
]


# ── Builders ──────────────────────────────────────────────────

def build_escalation_card(
    escalation_record: dict[str, Any],
    session_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured action card for an escalation event.

    Args:
        escalation_record: The EscalationRecord dict from the System Log.
        session_context:   Optional dict with session summary info
                           (domain, student pseudonym, turn count).

    Returns:
        A dict conforming to the action-card-schema-v1 JSON Schema.
    """
    record_id = escalation_record.get("record_id", "")
    trigger = escalation_record.get("trigger", "unknown")
    sla = escalation_record.get("sla_minutes", 30)
    domain_decision = escalation_record.get("domain_lib_decision") or {}
    target_role = escalation_record.get("target_role", "domain_authority")

    ctx: dict[str, Any] = {
        "trigger": trigger,
        "sla_minutes": sla,
        "target_role": target_role,
        "session_id": escalation_record.get("session_id", ""),
        "actor_id": escalation_record.get("actor_id", ""),
        "domain_lib_tier": domain_decision.get("tier"),
        "domain_alert_flag": domain_decision.get("domain_alert_flag"),
    }
    if session_context:
        ctx["domain_id"] = session_context.get("domain_id", "")
        ctx["turn_count"] = session_context.get("turn_count")
        ctx["student_pseudonym"] = session_context.get("student_pseudonym", "")

    body = f"Escalation triggered: {trigger}"
    if sla:
        body += f" (SLA: {sla} min)"
    if domain_decision.get("domain_alert_flag"):
        body += f" — alert: {domain_decision['domain_alert_flag']}"

    return {
        "type": "action_card",
        "card_type": "escalation",
        "id": record_id,
        "title": "Escalation Alert",
        "body": body,
        "context": ctx,
        "actions": list(_ESCALATION_ACTIONS),
        "resolve_endpoint": f"/api/escalations/{record_id}/resolve",
        "metadata": {
            "timestamp_utc": escalation_record.get("timestamp_utc", ""),
            "task_id": escalation_record.get("task_id", ""),
            "assigned_room_id": escalation_record.get("assigned_room_id"),
            "escalation_target_id": escalation_record.get("escalation_target_id"),
        },
    }


def build_command_proposal_card(
    staged_command: dict[str, Any],
) -> dict[str, Any]:
    """Build a structured action card for a staged HITL command.

    Args:
        staged_command: The staged command entry from ``_STAGED_COMMANDS``.

    Returns:
        A dict conforming to the action-card-schema-v1 JSON Schema.
    """
    staged_id = staged_command.get("staged_id", "")
    parsed = staged_command.get("parsed_command") or {}
    operation = parsed.get("operation", "unknown")
    params = parsed.get("params") or {}
    original = staged_command.get("original_instruction", "")

    body = f"Admin command: {operation}"
    if original:
        body += f'\nInstruction: "{original[:200]}"'
    if params:
        summary_items = [f"{k}={v}" for k, v in list(params.items())[:5]]
        body += f"\nParams: {', '.join(summary_items)}"

    return {
        "type": "action_card",
        "card_type": "command_proposal",
        "id": staged_id,
        "title": "Command Proposal",
        "body": body,
        "context": {
            "operation": operation,
            "params": params,
            "target": parsed.get("target", ""),
            "original_instruction": original,
            "actor_id": staged_command.get("actor_id", ""),
            "expires_at": staged_command.get("expires_at"),
        },
        "actions": list(_COMMAND_ACTIONS),
        "resolve_endpoint": f"/api/admin/command/{staged_id}/resolve",
        "metadata": {
            "staged_at": staged_command.get("staged_at"),
            "expires_at": staged_command.get("expires_at"),
            "log_stage_record_id": staged_command.get("log_stage_record_id", ""),
        },
    }
