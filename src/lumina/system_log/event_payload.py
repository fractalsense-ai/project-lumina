"""
event_payload.py — Universal Event Payload

Defines the canonical event envelope that every Lumina subsystem emits
into the log bus.  The micro-router inspects ``level`` and ``category``
to decide where the event ends up (archive, dashboard, alert stream, or
immutable audit ledger).

The ``record`` field carries the hash-chained System Log record when
``level`` is ``AUDIT``; for all other levels it is ``None``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class LogLevel(str, Enum):
    """Severity / routing tier for a log event."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    AUDIT = "AUDIT"


@dataclass(frozen=True, slots=True)
class LogEvent:
    """Universal Event Payload — the single envelope emitted by every module.

    Fields:
        timestamp  ISO-8601 UTC timestamp (auto-filled by ``create_event``).
        source     Dotted module/subsystem name (e.g. ``ppa_orchestrator``).
        level      One of :class:`LogLevel`.
        category   Free-form tag for micro-router filtering
                   (``invariant_check``, ``session_lifecycle``, ``hash_chain``, …).
        message    Human-readable summary.
        data       Arbitrary structured payload (metrics, IDs, diagnostics).
        record     Hash-chained System Log record dict when ``level`` is AUDIT.
    """

    timestamp: str
    source: str
    level: LogLevel
    category: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    record: dict[str, Any] | None = None
    domain_id: str | None = None

    # -- helpers --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (``level`` becomes its string value)."""
        d = asdict(self)
        d["level"] = self.level.value
        return d


def create_event(
    source: str,
    level: LogLevel | str,
    category: str,
    message: str,
    *,
    data: dict[str, Any] | None = None,
    record: dict[str, Any] | None = None,
    domain_id: str | None = None,
) -> LogEvent:
    """Factory that stamps the current UTC time and coerces *level*."""
    if isinstance(level, str):
        level = LogLevel(level)
    return LogEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        source=source,
        level=level,
        category=category,
        message=message,
        data=data or {},
        record=record,
        domain_id=domain_id,
    )
