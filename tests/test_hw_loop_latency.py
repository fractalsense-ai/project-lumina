"""Tests for lumina.systools.hw_loop_latency."""
from __future__ import annotations

import asyncio

import pytest

from lumina.systools.hw_loop_latency import measure_loop_latency, measure_loop_latency_async


# ── Async probe ───────────────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.anyio
async def test_measure_loop_latency_async_returns_dict() -> None:
    result = await measure_loop_latency_async()
    assert result is not None
    assert "latency_ms" in result
    assert "expected_ms" in result
    assert "load_ratio" in result


@pytest.mark.unit
@pytest.mark.anyio
async def test_measure_loop_latency_async_latency_non_negative() -> None:
    result = await measure_loop_latency_async()
    assert result is not None
    assert result["latency_ms"] >= 0.0


@pytest.mark.unit
@pytest.mark.anyio
async def test_measure_loop_latency_async_load_ratio_calculation() -> None:
    result = await measure_loop_latency_async(expected_ms=2.0)
    assert result is not None
    assert result["expected_ms"] == 2.0
    # load_ratio = latency_ms / expected_ms
    expected_ratio = result["latency_ms"] / 2.0
    assert abs(result["load_ratio"] - expected_ratio) < 1e-6


@pytest.mark.unit
@pytest.mark.anyio
async def test_measure_loop_latency_async_zero_expected() -> None:
    result = await measure_loop_latency_async(expected_ms=0.0)
    assert result is not None
    assert result["load_ratio"] == 1.0  # fallback when expected_ms == 0


# ── Sync stub ─────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_sync_stub_returns_none() -> None:
    assert measure_loop_latency() is None
