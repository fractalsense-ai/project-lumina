"""
alert_store.py — Bounded In-Memory Event Stores

Provides two thread-safe bounded stores used by the micro-router:

    ``WarningStore``  — holds the last *N* WARNING-level events for the
                        admin dashboard (default 1 000).
    ``AlertStore``    — holds the last *N* ERROR / CRITICAL events for the
                        Chat UI immediate-alert stream (default 100).

Both stores are ``collections.deque``-backed so older entries are evicted
automatically when the bound is reached.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Sequence

from lumina.system_log.event_payload import LogEvent


class WarningStore:
    """Bounded ring buffer for WARNING-level events (admin dashboard)."""

    def __init__(self, maxlen: int = 1000) -> None:
        self._buf: deque[LogEvent] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def push(self, event: LogEvent) -> None:
        with self._lock:
            self._buf.append(event)

    def query(
        self,
        limit: int = 50,
        offset: int = 0,
        category_filter: str | None = None,
        domain_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            items: Sequence[LogEvent] = list(self._buf)
        if category_filter:
            items = [e for e in items if e.category == category_filter]
        if domain_id:
            items = [e for e in items if e.domain_id == domain_id]
        # Most-recent first.
        items = list(reversed(items))
        page = items[offset : offset + limit]
        return [e.to_dict() for e in page]

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)


class AlertStore:
    """Bounded ring buffer for ERROR / CRITICAL events (Chat UI alerts)."""

    def __init__(self, maxlen: int = 100) -> None:
        self._buf: deque[LogEvent] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def push(self, event: LogEvent) -> None:
        with self._lock:
            self._buf.append(event)

    def query(
        self,
        limit: int = 20,
        offset: int = 0,
        domain_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._buf)
        if domain_id:
            items = [e for e in items if e.domain_id == domain_id]
        items = list(reversed(items))
        page = items[offset : offset + limit]
        return [e.to_dict() for e in page]

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)


# ── Module-level singletons (wired by log_router) ────────────

warning_store = WarningStore()
alert_store = AlertStore()
