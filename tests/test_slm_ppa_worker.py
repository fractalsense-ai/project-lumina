"""Tests for lumina.core.slm_ppa_worker — async SLM PPA enrichment worker.

Covers lifecycle (start/stop/is_running), enrichment dispatch, and
graceful shutdown via sentinel.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lumina.core.slm_ppa_worker import (
    EnrichmentKind,
    EnrichmentRequest,
    enqueue,
    is_running,
    start,
    stop,
)


def _run(coro):
    """Run an async coroutine in a fresh event loop."""
    return asyncio.run(coro)


def _reset_worker():
    """Reset worker module-level state between tests."""
    import lumina.core.slm_ppa_worker as w
    w._running = False
    w._worker_task = None
    w._queue = asyncio.Queue()


# ── Lifecycle ─────────────────────────────────────────────────────────────────


class TestWorkerLifecycle:

    @pytest.mark.unit
    def test_start_sets_running(self) -> None:
        async def _test():
            _reset_worker()
            await start()
            assert is_running()
            await stop()
            assert not is_running()
        _run(_test())

    @pytest.mark.unit
    def test_duplicate_start_is_noop(self) -> None:
        async def _test():
            import lumina.core.slm_ppa_worker as w
            _reset_worker()
            await start()
            task1 = w._worker_task
            await start()  # duplicate — should be no-op
            assert w._worker_task is task1
            await stop()
        _run(_test())

    @pytest.mark.unit
    def test_stop_without_start_is_safe(self) -> None:
        async def _test():
            _reset_worker()
            await stop()  # should not raise
        _run(_test())


# ── Enrichment Dispatch ───────────────────────────────────────────────────────


class TestEnrichmentDispatch:

    @pytest.mark.unit
    def test_physics_enrichment(self) -> None:
        async def _test():
            _reset_worker()
            with patch(
                "lumina.core.slm_ppa_worker._enrich_physics",
                new_callable=AsyncMock,
                return_value={"matched_invariants": ["inv1"]},
            ) as mock_physics:
                await start()
                result = await enqueue(
                    EnrichmentKind.PHYSICS_CONTEXT,
                    {"incoming_signals": {"x": 1}, "domain_physics": {}},
                )
                assert result == {"matched_invariants": ["inv1"]}
                mock_physics.assert_awaited_once()
                await stop()
        _run(_test())

    @pytest.mark.unit
    def test_command_enrichment(self) -> None:
        async def _test():
            _reset_worker()
            with patch(
                "lumina.core.slm_ppa_worker._enrich_command",
                new_callable=AsyncMock,
                return_value={"operation": "update_domain_physics", "target": "t", "params": {}},
            ) as mock_cmd:
                await start()
                result = await enqueue(
                    EnrichmentKind.COMMAND_PARSE,
                    {"natural_language": "update something"},
                )
                assert result is not None
                assert result["operation"] == "update_domain_physics"
                mock_cmd.assert_awaited_once()
                await stop()
        _run(_test())

    @pytest.mark.unit
    def test_enrichment_failure_propagates(self) -> None:
        async def _test():
            _reset_worker()
            with patch(
                "lumina.core.slm_ppa_worker._enrich_physics",
                new_callable=AsyncMock,
                side_effect=RuntimeError("SLM unavailable"),
            ):
                await start()
                with pytest.raises(RuntimeError, match="SLM unavailable"):
                    await enqueue(
                        EnrichmentKind.PHYSICS_CONTEXT,
                        {"incoming_signals": {}, "domain_physics": {}},
                    )
                await stop()
        _run(_test())


# ── EnrichmentRequest ─────────────────────────────────────────────────────────


class TestEnrichmentRequest:

    @pytest.mark.unit
    def test_request_has_future(self) -> None:
        async def _test():
            req = EnrichmentRequest(
                kind=EnrichmentKind.PHYSICS_CONTEXT,
                payload={"incoming_signals": {}, "domain_physics": {}},
            )
            assert isinstance(req.future, asyncio.Future)
        _run(_test())

    @pytest.mark.unit
    def test_enrichment_kind_values(self) -> None:
        assert EnrichmentKind.PHYSICS_CONTEXT.value == "physics_context"
        assert EnrichmentKind.COMMAND_PARSE.value == "command_parse"


# ── Log Bus Event Emission ────────────────────────────────────────────────────


class TestWorkerEventEmission:
    """Verify that the SLM PPA worker emits events to the log bus."""

    @pytest.mark.unit
    def test_emits_info_on_success(self) -> None:
        from lumina.system_log.event_payload import LogLevel
        import lumina.system_log.log_bus as bus

        received = []

        async def _test():
            _reset_worker()
            bus._running = False
            bus._task = None
            bus._queue = asyncio.Queue()
            bus._subscriptions.clear()

            bus.subscribe(lambda e: received.append(e), level_filter=[LogLevel.INFO])
            await bus.start()

            with patch(
                "lumina.core.slm_ppa_worker._enrich_physics",
                new_callable=AsyncMock,
                return_value={"matched_invariants": []},
            ):
                await start()
                await enqueue(
                    EnrichmentKind.PHYSICS_CONTEXT,
                    {"incoming_signals": {}, "domain_physics": {}},
                )
                await asyncio.sleep(0.05)
                await stop()

            await bus.stop()

        _run(_test())
        info_events = [e for e in received if e.source == "slm_ppa_worker"]
        assert len(info_events) >= 1
        assert info_events[0].category == "inference_parsing"

    @pytest.mark.unit
    def test_emits_warning_on_failure(self) -> None:
        from lumina.system_log.event_payload import LogLevel
        import lumina.system_log.log_bus as bus

        received = []

        async def _test():
            _reset_worker()
            bus._running = False
            bus._task = None
            bus._queue = asyncio.Queue()
            bus._subscriptions.clear()

            bus.subscribe(lambda e: received.append(e), level_filter=[LogLevel.WARNING])
            await bus.start()

            with patch(
                "lumina.core.slm_ppa_worker._enrich_physics",
                new_callable=AsyncMock,
                side_effect=RuntimeError("SLM down"),
            ):
                await start()
                with pytest.raises(RuntimeError):
                    await enqueue(
                        EnrichmentKind.PHYSICS_CONTEXT,
                        {"incoming_signals": {}, "domain_physics": {}},
                    )
                await asyncio.sleep(0.05)
                await stop()

            await bus.stop()

        _run(_test())
        warn_events = [e for e in received if e.source == "slm_ppa_worker"]
        assert len(warn_events) >= 1
        assert "SLM down" in warn_events[0].message
