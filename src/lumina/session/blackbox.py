"""blackbox.py — Black-box snapshot capture and persistence.

When a trigger fires, freezes the conversation ring buffer, telemetry
window, recent trace events, session state, and system health into a
single JSON file under ``data/blackbox/``.

Writes are atomic (tmp → rename) for crash safety.  Old snapshots are
auto-purged when ``max_files`` is exceeded.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("lumina.blackbox")

DEFAULT_OUTPUT_DIR = Path("data/blackbox")
DEFAULT_MAX_FILES: int = 100


@dataclass
class BlackBoxSnapshot:
    """Immutable diagnostic package captured on trigger."""

    timestamp_utc: str
    session_id: str
    domain_id: str
    trigger_type: str
    trigger_source: str
    conversation_buffer: list[dict[str, Any]] = field(default_factory=list)
    telemetry_window: dict[str, Any] = field(default_factory=dict)
    trace_events: list[dict[str, Any]] = field(default_factory=list)
    session_state: dict[str, Any] = field(default_factory=dict)
    system_health: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"


def capture_blackbox(
    session_id: str,
    domain_id: str,
    trigger_type: str,
    trigger_source: str,
    *,
    ring_buffer_snapshot: list[Any] | None = None,
    telemetry_summary: dict[str, Any] | None = None,
    recent_trace_events: list[dict[str, Any]] | None = None,
    session_state: dict[str, Any] | None = None,
    system_health: dict[str, Any] | None = None,
) -> BlackBoxSnapshot:
    """Assemble a ``BlackBoxSnapshot`` from the current session state."""
    conv_records: list[dict[str, Any]] = []
    if ring_buffer_snapshot:
        for rec in ring_buffer_snapshot:
            if hasattr(rec, "__dataclass_fields__"):
                conv_records.append(asdict(rec))
            elif isinstance(rec, dict):
                conv_records.append(rec)

    return BlackBoxSnapshot(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        session_id=session_id,
        domain_id=domain_id,
        trigger_type=trigger_type,
        trigger_source=trigger_source,
        conversation_buffer=conv_records,
        telemetry_window=telemetry_summary or {},
        trace_events=recent_trace_events or [],
        session_state=session_state or {},
        system_health=system_health or {},
    )


def write_blackbox(
    snapshot: BlackBoxSnapshot,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    max_files: int = DEFAULT_MAX_FILES,
) -> Path:
    """Write *snapshot* to a JSON file and return the path.

    Uses atomic write (write to tmp, then rename).  Prunes oldest files
    when the directory exceeds *max_files*.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = snapshot.timestamp_utc.replace(":", "-").replace("+", "p")
    filename = f"{snapshot.session_id}_{ts}.json"
    target = output_dir / filename

    payload = asdict(snapshot)

    # Atomic write: tmp file → rename
    fd, tmp_path = tempfile.mkstemp(dir=str(output_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str, ensure_ascii=False)
        os.replace(tmp_path, str(target))
    except BaseException:
        # Clean up partial write on any failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    log.info("Black-box snapshot written: %s", target)

    # Prune oldest files if over limit
    _prune_old_snapshots(output_dir, max_files)

    return target


def _prune_old_snapshots(output_dir: Path, max_files: int) -> None:
    """Remove oldest .json files when the directory exceeds *max_files*."""
    json_files = sorted(output_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    excess = len(json_files) - max_files
    for f in json_files[:excess]:
        try:
            f.unlink()
            log.debug("Pruned old blackbox snapshot: %s", f.name)
        except OSError:
            pass
