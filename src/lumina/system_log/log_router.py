"""
log_router.py — System Log Micro-Router

Implements the routing rules from the whiteboard:

    INFO / DEBUG   → ``_route_archive``   — rolling log file (Python logging)
    WARNING        → ``_route_staging``   — admin dashboard queue (WarningStore)
    ERROR/CRITICAL → ``_route_immediate`` — persistent error log + alert queue
    AUDIT          → ``_route_audit``     — immutable write-only ledger

Each route handler is registered as a subscriber on the central log bus.
The router's ``start()`` / ``stop()`` are called from the FastAPI
startup / shutdown hooks, immediately after the bus itself is started.

Design note:
    The AUDIT route does **not** perform the JSONL append itself.  The
    ``SystemLogWriter`` still owns hash-chaining and record formatting.
    By the time an AUDIT event reaches the bus the record has already
    been appended (or will be appended by the writer's own callback).
    The AUDIT route exists so that secondary consumers (dashboards,
    analytics) can observe audit-level events without touching the
    ledger files.
"""

from __future__ import annotations

import logging

from lumina.system_log.event_payload import LogEvent, LogLevel
from lumina.system_log import log_bus
from lumina.system_log.alert_store import warning_store, alert_store

# Rolling log files go through Python's standard logging.
_archive_log = logging.getLogger("lumina.archive")
_error_log = logging.getLogger("lumina.errors")
_audit_log = logging.getLogger("lumina.audit")


# ── Route handlers ───────────────────────────────────────────


def _route_archive(event: LogEvent) -> None:
    """INFO / DEBUG → rolling archive log."""
    _archive_log.log(
        logging.DEBUG if event.level is LogLevel.DEBUG else logging.INFO,
        "[%s] %s — %s",
        event.source,
        event.category,
        event.message,
    )


def _route_staging(event: LogEvent) -> None:
    """WARNING → admin dashboard queue."""
    _archive_log.warning("[%s] %s — %s", event.source, event.category, event.message)
    warning_store.push(event)


def _route_immediate(event: LogEvent) -> None:
    """ERROR / CRITICAL → persistent error log + alert queue."""
    _error_log.error("[%s] %s — %s", event.source, event.category, event.message)
    alert_store.push(event)


def _route_audit(event: LogEvent) -> None:
    """AUDIT → observe audit-level events (ledger write is done by SystemLogWriter)."""
    _audit_log.info("[AUDIT:%s] %s — %s", event.source, event.category, event.message)


# ── Lifecycle ────────────────────────────────────────────────

_started: bool = False


def start() -> None:
    """Register route handlers as bus subscribers."""
    global _started
    if _started:
        return

    log_bus.subscribe(
        _route_archive,
        level_filter=[LogLevel.DEBUG, LogLevel.INFO],
    )
    log_bus.subscribe(
        _route_staging,
        level_filter=[LogLevel.WARNING],
    )
    log_bus.subscribe(
        _route_immediate,
        level_filter=[LogLevel.ERROR, LogLevel.CRITICAL],
    )
    log_bus.subscribe(
        _route_audit,
        level_filter=[LogLevel.AUDIT],
    )

    _started = True


def stop() -> None:
    """Clean-up hook (currently a no-op; bus handles subscriber teardown)."""
    global _started
    _started = False
