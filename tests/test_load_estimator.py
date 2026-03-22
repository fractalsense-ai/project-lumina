"""Tests for lumina.daemon.load_estimator."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from lumina.daemon.load_estimator import (
    DEFAULT_IDLE_THRESHOLD,
    DEFAULT_WEIGHTS,
    LoadEstimator,
    LoadSnapshot,
)


# ── LoadSnapshot dataclass ────────────────────────────────────────────────────


@pytest.mark.unit
def test_load_snapshot_defaults() -> None:
    snap = LoadSnapshot()
    assert snap.timestamp == 0.0
    assert snap.loop_latency_ms is None
    assert snap.inflight_requests is None
    assert snap.gpu_pct is None
    assert snap.load_score == 0.0
    assert snap.is_idle is False


# ── LoadEstimator — all probes return values ──────────────────────────────────


@pytest.mark.unit
@pytest.mark.anyio
async def test_sample_all_probes() -> None:
    estimator = LoadEstimator()
    with (
        patch(
            "lumina.systools.hw_loop_latency.measure_loop_latency_async",
            new_callable=AsyncMock,
            return_value={"latency_ms": 5.0, "expected_ms": 1.0, "load_ratio": 5.0},
        ),
        patch(
            "lumina.systools.hw_http_queue.get_inflight_requests",
            return_value={"inflight": 4, "max_seen": 10},
        ),
        patch(
            "lumina.systools.hw_gpu.get_gpu_usage",
            return_value={"vram_used_mb": 500.0, "vram_total_mb": 1000.0, "vram_pct_used": 50.0, "gpu_load_pct": 40.0},
        ),
    ):
        snap = await estimator.sample()

    assert snap.loop_latency_ms == 5.0
    assert snap.inflight_requests == 4
    assert snap.gpu_pct == 50.0
    assert 0.0 <= snap.load_score <= 1.0


@pytest.mark.unit
@pytest.mark.anyio
async def test_sample_high_load_not_idle() -> None:
    estimator = LoadEstimator(idle_threshold=0.1)
    with (
        patch(
            "lumina.systools.hw_loop_latency.measure_loop_latency_async",
            new_callable=AsyncMock,
            return_value={"latency_ms": 50.0, "expected_ms": 1.0, "load_ratio": 50.0},
        ),
        patch(
            "lumina.systools.hw_http_queue.get_inflight_requests",
            return_value={"inflight": 20, "max_seen": 20},
        ),
        patch(
            "lumina.systools.hw_gpu.get_gpu_usage",
            return_value={"vram_used_mb": 900.0, "vram_total_mb": 1000.0, "vram_pct_used": 90.0, "gpu_load_pct": 80.0},
        ),
    ):
        snap = await estimator.sample()

    assert snap.is_idle is False
    assert snap.load_score > 0.5


# ── LoadEstimator — some probes return None (redistribution) ──────────────────


@pytest.mark.unit
@pytest.mark.anyio
async def test_sample_gpu_none_redistributes_weight() -> None:
    estimator = LoadEstimator()
    with (
        patch(
            "lumina.systools.hw_loop_latency.measure_loop_latency_async",
            new_callable=AsyncMock,
            return_value={"latency_ms": 10.0, "expected_ms": 1.0, "load_ratio": 10.0},
        ),
        patch(
            "lumina.systools.hw_http_queue.get_inflight_requests",
            return_value={"inflight": 2, "max_seen": 5},
        ),
        patch("lumina.systools.hw_gpu.get_gpu_usage", return_value=None),
    ):
        snap = await estimator.sample()

    assert snap.gpu_pct is None
    # Score should still compute from the remaining two probes
    assert 0.0 <= snap.load_score <= 1.0


@pytest.mark.unit
@pytest.mark.anyio
async def test_sample_all_probes_none() -> None:
    estimator = LoadEstimator()
    with (
        patch(
            "lumina.systools.hw_loop_latency.measure_loop_latency_async",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch("lumina.systools.hw_http_queue.get_inflight_requests", return_value=None),
        patch("lumina.systools.hw_gpu.get_gpu_usage", return_value=None),
    ):
        snap = await estimator.sample()

    assert snap.load_score == 0.0
    assert snap.is_idle is True  # 0.0 < 0.20


# ── LoadEstimator — idle detection ───────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.anyio
async def test_idle_when_load_below_threshold() -> None:
    estimator = LoadEstimator(idle_threshold=0.5)
    with (
        patch(
            "lumina.systools.hw_loop_latency.measure_loop_latency_async",
            new_callable=AsyncMock,
            return_value={"latency_ms": 1.0, "expected_ms": 1.0, "load_ratio": 1.0},
        ),
        patch(
            "lumina.systools.hw_http_queue.get_inflight_requests",
            return_value={"inflight": 0, "max_seen": 0},
        ),
        patch("lumina.systools.hw_gpu.get_gpu_usage", return_value=None),
    ):
        snap = await estimator.sample()

    assert snap.is_idle is True


# ── configure() hot-reload ────────────────────────────────────────────────────


@pytest.mark.unit
def test_configure_updates_weights() -> None:
    estimator = LoadEstimator()
    estimator.configure({
        "probe_weights": {"loop_latency": 0.8, "http_queue": 0.1, "gpu": 0.1},
        "idle_threshold": 0.30,
    })
    assert estimator._weights["loop_latency"] == 0.8
    assert estimator._idle_threshold == 0.30
