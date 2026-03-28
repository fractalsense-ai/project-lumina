"""Tests for lumina.daemon.load_estimator — TelemetryWindow and sliding-window features."""
from __future__ import annotations

import pytest

from lumina.daemon.load_estimator import (
    LoadEstimator,
    LoadSnapshot,
    TelemetrySummary,
    TelemetryWindow,
    DEFAULT_WINDOW_DEPTH,
)


# ── TelemetryWindow basics ───────────────────────────────────────────────────


@pytest.mark.unit
def test_empty_window_summary() -> None:
    w = TelemetryWindow(max_depth=10)
    s = w.summary()
    assert s.json_summary["load_trajectory"] == "stable"
    assert s.json_summary["samples"] == 0
    assert len(s.numeric_vector) == 6


@pytest.mark.unit
def test_window_push_and_depth() -> None:
    w = TelemetryWindow(max_depth=5)
    for i in range(5):
        w.push(LoadSnapshot(load_score=i * 0.1))
    assert w.depth == 5


@pytest.mark.unit
def test_window_eviction() -> None:
    """Pushing N+1 snapshots into a window of size N evicts the oldest."""
    w = TelemetryWindow(max_depth=5)
    for i in range(7):
        w.push(LoadSnapshot(load_score=i * 0.1))
    assert w.depth == 5
    s = w.summary()
    # Oldest two (0.0, 0.1) should be evicted; trough should be 0.2
    assert s.json_summary["trough"] == 0.2


@pytest.mark.unit
def test_window_clear() -> None:
    w = TelemetryWindow(max_depth=5)
    w.push(LoadSnapshot(load_score=0.5))
    w.clear()
    assert w.depth == 0


# ── Trajectory classification ────────────────────────────────────────────────


@pytest.mark.unit
def test_trajectory_rising() -> None:
    w = TelemetryWindow(max_depth=10)
    for i in range(10):
        w.push(LoadSnapshot(load_score=0.1 + i * 0.08))
    s = w.summary()
    assert s.json_summary["load_trajectory"] == "rising"


@pytest.mark.unit
def test_trajectory_falling() -> None:
    w = TelemetryWindow(max_depth=10)
    for i in range(10):
        w.push(LoadSnapshot(load_score=0.9 - i * 0.08))
    s = w.summary()
    assert s.json_summary["load_trajectory"] == "falling"


@pytest.mark.unit
def test_trajectory_stable() -> None:
    w = TelemetryWindow(max_depth=10)
    for _ in range(10):
        w.push(LoadSnapshot(load_score=0.5))
    s = w.summary()
    assert s.json_summary["load_trajectory"] == "stable"


# ── Dual-format output ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_summary_dual_format() -> None:
    w = TelemetryWindow(max_depth=5)
    for i in range(5):
        w.push(LoadSnapshot(load_score=0.2 + i * 0.1))
    s = w.summary()
    # JSON summary keys
    assert "load_trajectory" in s.json_summary
    assert "load_delta_pct" in s.json_summary
    assert "curve" in s.json_summary
    assert "baseline" in s.json_summary
    assert "current" in s.json_summary
    assert "ewma" in s.json_summary
    assert "samples" in s.json_summary
    # Numeric vector
    assert len(s.numeric_vector) == 6
    assert all(isinstance(v, float) for v in s.numeric_vector)


# ── EWMA tracking ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_ewma_weights_recent() -> None:
    """EWMA should weight recent values more than distant ones."""
    w = TelemetryWindow(max_depth=20)
    # Push 10 low values, then a spike
    for _ in range(10):
        w.push(LoadSnapshot(load_score=0.1))
    w.push(LoadSnapshot(load_score=0.9))
    s = w.summary()
    # EWMA should be between 0.1 and 0.9, closer to 0.1 (since we had 10 low values)
    assert 0.1 < s.json_summary["ewma"] < 0.9


# ── Curve classification ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_curve_exponential() -> None:
    """Accelerating scores should be classified as exponential."""
    w = TelemetryWindow(max_depth=10)
    # Slow start, rapid end
    scores = [0.1, 0.12, 0.14, 0.16, 0.18, 0.25, 0.4, 0.6, 0.8, 0.95]
    for s in scores:
        w.push(LoadSnapshot(load_score=s))
    summary = w.summary()
    assert summary.json_summary["curve"] == "exponential"


@pytest.mark.unit
def test_curve_plateau() -> None:
    """Decelerating scores should be classified as plateau."""
    w = TelemetryWindow(max_depth=10)
    scores = [0.1, 0.35, 0.55, 0.68, 0.75, 0.78, 0.79, 0.795, 0.80, 0.80]
    for s in scores:
        w.push(LoadSnapshot(load_score=s))
    summary = w.summary()
    assert summary.json_summary["curve"] == "plateau"


# ── LoadEstimator integration ────────────────────────────────────────────────


@pytest.mark.unit
def test_estimator_window_depth_default() -> None:
    est = LoadEstimator()
    assert est.window.max_depth == DEFAULT_WINDOW_DEPTH


@pytest.mark.unit
def test_estimator_window_depth_custom() -> None:
    est = LoadEstimator(window_depth=50)
    assert est.window.max_depth == 50


@pytest.mark.unit
def test_estimator_get_window_summary() -> None:
    est = LoadEstimator()
    s = est.get_window_summary()
    assert isinstance(s, TelemetrySummary)
    assert s.json_summary["samples"] == 0


@pytest.mark.unit
def test_estimator_configure_window_depth() -> None:
    est = LoadEstimator(window_depth=10)
    assert est.window.max_depth == 10
    est.configure({"telemetry_window_depth": 30})
    assert est.window.max_depth == 30
