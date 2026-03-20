"""File Writer — deterministic actuator for staged files.

Writes a validated payload to its final destination using a template's
default structure as the skeleton.  The write is **atomic**: content goes
to a temporary file first and is renamed only on success, ensuring no
corrupt partial files on disk.

This module never calls an LLM — it is a pure data transform + I/O.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from lumina.staging.template_registry import TemplateRegistry

log = logging.getLogger(__name__)


def write_from_template(
    template_id: str,
    validated_payload: dict[str, Any],
    target_path: Path,
) -> Path:
    """Merge *validated_payload* into the template skeleton and write atomically.

    Parameters
    ----------
    template_id:
        Must be a registered template ID.
    validated_payload:
        Already-validated dict (the staging service is responsible for
        running inspection before calling this).
    target_path:
        Absolute path for the output file.

    Returns
    -------
    The resolved *target_path* on success.

    Raises
    ------
    ValueError  — unknown template or missing required fields.
    OSError     — filesystem I/O failure.
    """
    template = TemplateRegistry.require(template_id)

    # Enforce required fields
    missing = [f for f in template.required_fields if f not in validated_payload]
    if missing:
        raise ValueError(
            f"Payload missing required fields for template "
            f"{template_id!r}: {missing}"
        )

    # Merge: defaults ← payload (payload wins)
    merged = _deep_merge(template.default_structure, validated_payload)

    # Serialize
    if template.file_format == "yaml":
        content = _to_yaml(merged)
    else:
        content = json.dumps(merged, indent=2, ensure_ascii=False) + "\n"

    # Atomic write: temp file → rename
    target_path = target_path.resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        dir=str(target_path.parent),
        prefix=".lumina_stage_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_name, str(target_path))
    except BaseException:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

    log.info("Wrote staged file to %s (%d bytes)", target_path, len(content))
    return target_path


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *overlay* onto a copy of *base*.  Overlay wins."""
    result = dict(base)
    for key, value in overlay.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _to_yaml(data: dict[str, Any]) -> str:
    """Minimal YAML serialiser for simple nested dicts/lists/scalars.

    Uses ``lumina.core.yaml_loader`` round-trip if available, otherwise
    falls back to a compact JSON representation (still valid YAML).
    """
    try:
        import yaml as _yaml  # type: ignore[import-untyped]
        return _yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
    except ImportError:
        # JSON is a subset of YAML — perfectly valid
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
