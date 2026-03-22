"""Tests for lumina.system_log.log_bus — async event bus."""
from __future__ import annotations

import asyncio

import pytest

from lumina.system_log.event_payload import LogEvent, LogLevel, create_event
import lumina.system_log.log_bus as bus


def _run(coro):
    return asyncio.run(coro)


def _reset_bus():
    """Reset module-level bus state between tests."""
    bus._running = False
    bus._task = None
    bus._queue = asyncio.Queue()
    bus._subscriptions.clear()


# ── Lifecycle ──────────────────────────────────────────────────────


class TestBusLifecycle:

    @pytest.mark.unit
    def test_start_stop(self) -> None:
        async def _test():
            _reset_bus()
            await bus.start()
            assert bus.is_running()
            await bus.stop()
            assert not bus.is_running()
        _run(_test())

    @pytest.mark.unit
    def test_duplicate_start_is_noop(self) -> None:
        async def _test():
            _reset_bus()
            await bus.start()
            await bus.start()  # should not raise
            assert bus.is_running()
            await bus.stop()
        _run(_test())


# ── Subscribe & emit_async ─────────────────────────────────────────


class TestEmitAsync:

    @pytest.mark.unit
    def test_subscriber_receives_event(self) -> None:
        received: list[LogEvent] = []

        async def _test():
            _reset_bus()
            bus.subscribe(lambda e: received.append(e))
            await bus.start()
            evt = create_event("test", LogLevel.INFO, "cat", "hello")
            await bus.emit_async(evt)
            # Give dispatch loop a tick to process.
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(received) == 1
        assert received[0].message == "hello"

    @pytest.mark.unit
    def test_level_filter(self) -> None:
        received: list[LogEvent] = []

        async def _test():
            _reset_bus()
            bus.subscribe(lambda e: received.append(e), level_filter=[LogLevel.WARNING])
            await bus.start()
            await bus.emit_async(create_event("t", LogLevel.INFO, "c", "skip"))
            await bus.emit_async(create_event("t", LogLevel.WARNING, "c", "keep"))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(received) == 1
        assert received[0].level is LogLevel.WARNING

    @pytest.mark.unit
    def test_category_filter(self) -> None:
        received: list[LogEvent] = []

        async def _test():
            _reset_bus()
            bus.subscribe(lambda e: received.append(e), category_filter=["hash_chain"])
            await bus.start()
            await bus.emit_async(create_event("t", LogLevel.AUDIT, "hash_chain", "a"))
            await bus.emit_async(create_event("t", LogLevel.INFO, "other", "b"))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(received) == 1
        assert received[0].category == "hash_chain"

    @pytest.mark.unit
    def test_async_subscriber(self) -> None:
        received: list[LogEvent] = []

        async def _cb(e: LogEvent) -> None:
            received.append(e)

        async def _test():
            _reset_bus()
            bus.subscribe(_cb, is_async=True)
            await bus.start()
            await bus.emit_async(create_event("t", LogLevel.INFO, "c", "async"))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(received) == 1


# ── Sync emit ──────────────────────────────────────────────────────


class TestSyncEmit:

    @pytest.mark.unit
    def test_emit_when_not_running_is_noop(self) -> None:
        _reset_bus()
        # Should not raise.
        bus.emit(create_event("t", LogLevel.INFO, "c", "dropped"))

    @pytest.mark.unit
    def test_emit_from_running_loop(self) -> None:
        received: list[LogEvent] = []

        async def _test():
            _reset_bus()
            bus.subscribe(lambda e: received.append(e))
            await bus.start()
            bus.emit(create_event("t", LogLevel.ERROR, "c", "sync"))
            await asyncio.sleep(0.05)
            await bus.stop()

        _run(_test())
        assert len(received) == 1
        assert received[0].message == "sync"


# ── clear_subscriptions ───────────────────────────────────────────


class TestClearSubscriptions:

    @pytest.mark.unit
    def test_clear(self) -> None:
        _reset_bus()
        bus.subscribe(lambda e: None)
        assert len(bus._subscriptions) == 1
        bus.clear_subscriptions()
        assert len(bus._subscriptions) == 0
