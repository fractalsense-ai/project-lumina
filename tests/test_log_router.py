"""Tests for lumina.system_log.log_router — micro-router routing rules."""
from __future__ import annotations

import asyncio

import pytest

from lumina.system_log.event_payload import LogLevel, create_event
from lumina.system_log.alert_store import AlertStore, WarningStore
import lumina.system_log.log_bus as bus
import lumina.system_log.log_router as router
import lumina.system_log.alert_store as _store_mod


def _run(coro):
    return asyncio.run(coro)


def _reset():
    """Reset both bus and router state between tests."""
    bus._running = False
    bus._task = None
    bus._queue = asyncio.Queue()
    bus._subscriptions.clear()
    router._started = False
    # Replace module-level stores with fresh instances.
    _store_mod.warning_store = WarningStore()
    _store_mod.alert_store = AlertStore()
    # Also patch the router's local references.
    router.warning_store = _store_mod.warning_store
    router.alert_store = _store_mod.alert_store


class TestRouteArchive:

    @pytest.mark.unit
    def test_info_reaches_archive_only(self) -> None:
        """INFO events should only reach the archive handler, not stores."""
        async def _test():
            _reset()
            router.start()
            await bus.start()
            await bus.emit_async(create_event("t", LogLevel.INFO, "cat", "info msg"))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(_store_mod.warning_store) == 0
        assert len(_store_mod.alert_store) == 0

    @pytest.mark.unit
    def test_debug_reaches_archive_only(self) -> None:
        async def _test():
            _reset()
            router.start()
            await bus.start()
            await bus.emit_async(create_event("t", LogLevel.DEBUG, "cat", "dbg"))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(_store_mod.warning_store) == 0
        assert len(_store_mod.alert_store) == 0


class TestRouteStaging:

    @pytest.mark.unit
    def test_warning_goes_to_warning_store(self) -> None:
        async def _test():
            _reset()
            router.start()
            await bus.start()
            await bus.emit_async(create_event("t", LogLevel.WARNING, "inv", "bad"))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(_store_mod.warning_store) == 1
        assert len(_store_mod.alert_store) == 0


class TestRouteImmediate:

    @pytest.mark.unit
    def test_error_goes_to_alert_store(self) -> None:
        async def _test():
            _reset()
            router.start()
            await bus.start()
            await bus.emit_async(create_event("t", LogLevel.ERROR, "c", "err"))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(_store_mod.alert_store) == 1

    @pytest.mark.unit
    def test_critical_goes_to_alert_store(self) -> None:
        async def _test():
            _reset()
            router.start()
            await bus.start()
            await bus.emit_async(create_event("t", LogLevel.CRITICAL, "c", "crit"))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(_store_mod.alert_store) == 1


class TestRouteAudit:

    @pytest.mark.unit
    def test_audit_does_not_hit_stores(self) -> None:
        """AUDIT events are observed via the bus but don't land in warning/alert stores."""
        async def _test():
            _reset()
            router.start()
            await bus.start()
            rec = {"record_type": "TraceEvent", "record_id": "abc"}
            await bus.emit_async(create_event("t", LogLevel.AUDIT, "hash_chain", "m", record=rec))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(_store_mod.warning_store) == 0
        assert len(_store_mod.alert_store) == 0


class TestMixedRouting:

    @pytest.mark.unit
    def test_multiple_levels_route_correctly(self) -> None:
        async def _test():
            _reset()
            router.start()
            await bus.start()
            await bus.emit_async(create_event("t", LogLevel.INFO, "c", "i"))
            await bus.emit_async(create_event("t", LogLevel.WARNING, "c", "w"))
            await bus.emit_async(create_event("t", LogLevel.ERROR, "c", "e"))
            await bus.emit_async(create_event("t", LogLevel.CRITICAL, "c", "c"))
            await bus.emit_async(create_event("t", LogLevel.AUDIT, "c", "a"))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(_store_mod.warning_store) == 1
        assert len(_store_mod.alert_store) == 2  # ERROR + CRITICAL
