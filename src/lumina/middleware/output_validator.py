"""Schema-based output validation for LLM-generated payloads.

Validates structured LLM output (turn_data / evidence dicts) against the
``turn_input_schema`` declarations from domain runtime configs.  This is
the deterministic "checkpoint" in the Three-Tier Execution Pipeline that
ensures the LLM's output conforms to expected types and enumerations
*before* tool adapters or the orchestrator act on it.

The validator is deliberately lightweight — it checks types, required
fields, enums, and numeric bounds using only the stdlib, with no
dependency on ``jsonschema`` or Pydantic at runtime.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("lumina.middleware.output_validator")

# JSON-Schema-like type strings → Python types
_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


def _check_type(value: Any, schema_type: str | list[str]) -> bool:
    """Return True if *value* matches *schema_type* (single or union)."""
    if isinstance(schema_type, list):
        return any(_check_type(value, t) for t in schema_type)
    expected = _TYPE_MAP.get(schema_type)
    if expected is None:
        return True  # unknown type → pass (permissive)
    # Python bool is a subclass of int; treat bool as its own type.
    if schema_type == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, expected)


def validate_output(
    payload: dict[str, Any],
    schema: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Validate *payload* against a lightweight JSON-schema-like *schema*.

    Parameters
    ----------
    payload:
        The LLM-generated structured output (evidence / turn_data dict).
    schema:
        A dict mapping field names to field descriptors.  Each descriptor
        may contain:

        - ``type``  — ``"string"`` | ``"integer"`` | ``"number"`` |
          ``"boolean"`` | ``"array"`` | ``"object"`` or a list of types.
        - ``enum``  — list of allowed values.
        - ``required`` — ``True`` if the field must be present.
        - ``minimum`` / ``maximum`` — numeric bounds.
        - ``default`` — default value (used to fill missing optional fields).

    Returns
    -------
    (valid, violations):
        ``valid`` is ``True`` when no violations were found.
        ``violations`` is a list of human-readable error strings.
    """
    violations: list[str] = []

    for field_name, field_spec in schema.items():
        if not isinstance(field_spec, dict):
            continue

        value = payload.get(field_name)
        is_required = field_spec.get("required", False)

        # ── Required-field check ──
        if value is None and field_name not in payload:
            if is_required:
                violations.append(f"Missing required field: {field_name}")
            continue

        # ── Type check ──
        declared_type = field_spec.get("type")
        if declared_type is not None and value is not None:
            if not _check_type(value, declared_type):
                violations.append(
                    f"Type mismatch for '{field_name}': "
                    f"expected {declared_type}, got {type(value).__name__}"
                )

        # ── Enum check ──
        allowed = field_spec.get("enum")
        if allowed is not None and value not in allowed:
            violations.append(
                f"Invalid value for '{field_name}': "
                f"{value!r} not in {allowed}"
            )

        # ── Numeric bounds ──
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            minimum = field_spec.get("minimum")
            if minimum is not None and value < minimum:
                violations.append(
                    f"Value for '{field_name}' ({value}) below minimum ({minimum})"
                )
            maximum = field_spec.get("maximum")
            if maximum is not None and value > maximum:
                violations.append(
                    f"Value for '{field_name}' ({value}) above maximum ({maximum})"
                )

    return (len(violations) == 0, violations)


def sanitize_output(
    payload: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    """Return a copy of *payload* with missing optional fields filled from defaults.

    Fields that are not declared in *schema* are passed through unchanged.
    Only fields with a ``"default"`` key in their schema descriptor are
    filled; fields without defaults remain absent.
    """
    result = dict(payload)
    for field_name, field_spec in schema.items():
        if not isinstance(field_spec, dict):
            continue
        if field_name not in result and "default" in field_spec:
            result[field_name] = field_spec["default"]
    return result
