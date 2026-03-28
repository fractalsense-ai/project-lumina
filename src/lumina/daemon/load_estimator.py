"""load_estimator.py — Weighted load-score aggregator with sliding-window telemetry.

Aggregates the three load probes (event-loop latency, in-flight HTTP
requests, GPU VRAM) into a single 0.0–1.0 ``load_score``.  When a probe
returns ``None`` its weight is redistributed among the remaining probes
so the score degrades gracefully.

The ``TelemetryWindow`` maintains a bounded history of snapshots and
computes deterministic curve summaries (trajectory, delta, curve type)
using EWMA — no LLM involved.

Used by ``resource_monitor.ResourceMonitorDaemon`` each poll cycle.
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


# ── Snapshot type ─────────────────────────────────────────────────────────────

@dataclass
class LoadSnapshot:
    """Point-in-time load reading produced by ``LoadEstimator.sample()``."""

    timestamp: float = 0.0
    loop_latency_ms: float | None = None
    inflight_requests: int | None = None
    gpu_pct: float | None = None
    load_score: float = 0.0
    is_idle: bool = False


# ── Telemetry window types ────────────────────────────────────────────────────

DEFAULT_WINDOW_DEPTH: int = 20
_EWMA_ALPHA: float = 0.3  # smoothing factor — higher = more weight on recent


@dataclass
class TelemetrySummary:
    """Dual-format telemetry summary produced by ``TelemetryWindow``."""

    json_summary: dict[str, Any] = field(default_factory=dict)
    numeric_vector: list[float] = field(default_factory=list)


# Trajectory codes for the numeric vector (index 5).
_TRAJECTORY_CODES: dict[str, float] = {
    "rising": 1.0,
    "falling": -1.0,
    "stable": 0.0,
    "spiking": 2.0,
    "cliff_drop": -2.0,
}


class TelemetryWindow:
    """Bounded sliding window of ``LoadSnapshot`` values with EWMA curve math.

    All computation is deterministic — no LLM/SLM involvement.
    """

    def __init__(self, max_depth: int = DEFAULT_WINDOW_DEPTH) -> None:
        self._buf: deque[LoadSnapshot] = deque(maxlen=max(max_depth, 2))
        self._ewma: float = 0.0
        self._ewma_primed: bool = False

    # ── Mutators ──────────────────────────────────────────────

    def push(self, snap: LoadSnapshot) -> None:
        """Append a snapshot and update the EWMA."""
        self._buf.append(snap)
        if not self._ewma_primed:
            self._ewma = snap.load_score
            self._ewma_primed = True
        else:
            self._ewma = _EWMA_ALPHA * snap.load_score + (1 - _EWMA_ALPHA) * self._ewma

    def clear(self) -> None:
        self._buf.clear()
        self._ewma = 0.0
        self._ewma_primed = False

    # ── Queries ───────────────────────────────────────────────

    @property
    def depth(self) -> int:
        return len(self._buf)

    @property
    def max_depth(self) -> int:
        return self._buf.maxlen  # type: ignore[return-value]

    def summary(self) -> TelemetrySummary:
        """Return a dual-format summary of the current window state."""
        if not self._buf:
            return TelemetrySummary(
                json_summary={"load_trajectory": "stable", "samples": 0},
                numeric_vector=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            )

        scores = [s.load_score for s in self._buf]
        current = scores[-1]
        baseline = sum(scores) / len(scores)
        peak = max(scores)
        trough = min(scores)

        trajectory = self._classify_trajectory(scores)
        delta_pct = self._compute_delta_pct(scores)
        curve = self._classify_curve(scores)

        traj_code = _TRAJECTORY_CODES.get(trajectory, 0.0)

        return TelemetrySummary(
            json_summary={
                "load_trajectory": trajectory,
                "load_delta_pct": round(delta_pct, 1),
                "curve": curve,
                "baseline": round(baseline, 3),
                "current": round(current, 3),
                "peak": round(peak, 3),
                "trough": round(trough, 3),
                "ewma": round(self._ewma, 3),
                "samples": len(scores),
            },
            numeric_vector=[
                round(current, 4),
                round(delta_pct, 4),
                round(baseline, 4),
                round(peak, 4),
                round(trough, 4),
                traj_code,
            ],
        )

    # ── Internal curve math ───────────────────────────────────

    @staticmethod
    def _classify_trajectory(scores: list[float]) -> str:
        """Classify the overall direction of the score sequence."""
        if len(scores) < 2:
            return "stable"

        # Compare recent half to older half
        mid = len(scores) // 2
        older = scores[:mid] or scores[:1]
        recent = scores[mid:] or scores[-1:]
        avg_old = sum(older) / len(older)
        avg_new = sum(recent) / len(recent)
        diff = avg_new - avg_old

        # Check for spike: latest value far above EWMA / mean
        if len(scores) >= 3:
            mean = sum(scores) / len(scores)
            if scores[-1] > mean + 0.3 and scores[-1] - scores[-2] > 0.2:
                return "spiking"
            if scores[-1] < mean - 0.3 and scores[-2] - scores[-1] > 0.2:
                return "cliff_drop"

        if abs(diff) < 0.05:
            return "stable"
        return "rising" if diff > 0 else "falling"

    @staticmethod
    def _compute_delta_pct(scores: list[float]) -> float:
        """Percentage change from oldest to newest score in the window."""
        if len(scores) < 2:
            return 0.0
        old = scores[0]
        new = scores[-1]
        if old == 0.0:
            return 0.0 if new == 0.0 else 100.0
        return ((new - old) / old) * 100.0

    @staticmethod
    def _classify_curve(scores: list[float]) -> str:
        """Simple curve shape heuristic: linear, exponential, or plateau."""
        if len(scores) < 3:
            return "linear"

        # Check if the rate of change is accelerating (exponential) or
        # decelerating (plateau) by comparing first-half delta to second-half.
        mid = len(scores) // 2
        first_delta = abs(scores[mid] - scores[0])
        second_delta = abs(scores[-1] - scores[mid])

        if first_delta < 0.01 and second_delta < 0.01:
            return "plateau"
        if second_delta > first_delta * 1.5:
            return "exponential"
        if second_delta < first_delta * 0.5:
            return "plateau"
        return "linear"


# ── Estimator ─────────────────────────────────────────────────────────────────

# Normalisation constants — map raw probe values to a 0.0–1.0 range.
_LATENCY_CEIL_MS: float = 50.0   # latency >= this → 1.0
_HTTP_CEIL: int = 20              # in-flight count >= this → 1.0
_GPU_CEIL_PCT: float = 100.0     # VRAM % used ceiling

DEFAULT_WEIGHTS: dict[str, float] = {
    "loop_latency": 0.5,
    "http_queue": 0.3,
    "gpu": 0.2,
}

DEFAULT_IDLE_THRESHOLD: float = 0.20


class LoadEstimator:
    """Aggregate three probes into a single load score.

    Maintains a sliding ``TelemetryWindow`` of recent snapshots and
    computes deterministic curve summaries for downstream consumers.

    Parameters
    ----------
    weights:
        Mapping of probe name → weight (must sum to 1.0).
    idle_threshold:
        ``load_score`` below this marks ``is_idle = True``.
    window_depth:
        Number of snapshots retained in the telemetry window.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        idle_threshold: float = DEFAULT_IDLE_THRESHOLD,
        window_depth: int = DEFAULT_WINDOW_DEPTH,
    ) -> None:
        self._weights = dict(weights or DEFAULT_WEIGHTS)
        self._idle_threshold = idle_threshold
        self._window = TelemetryWindow(max_depth=window_depth)

    # ── Public API ────────────────────────────────────────────

    async def sample(self) -> LoadSnapshot:
        """Collect one load snapshot by invoking all three probes."""
        snap = LoadSnapshot(timestamp=time.monotonic())

        raw: dict[str, float | None] = {}

        # — loop latency (async) —
        try:
            from lumina.systools.hw_loop_latency import measure_loop_latency_async
            result = await measure_loop_latency_async()
            if result is not None:
                snap.loop_latency_ms = result["latency_ms"]
                raw["loop_latency"] = min(result["latency_ms"] / _LATENCY_CEIL_MS, 1.0)
            else:
                raw["loop_latency"] = None
        except Exception:
            raw["loop_latency"] = None

        # — in-flight HTTP —
        try:
            from lumina.systools.hw_http_queue import get_inflight_requests
            result = get_inflight_requests()
            if result is not None:
                snap.inflight_requests = result["inflight"]
                raw["http_queue"] = min(result["inflight"] / _HTTP_CEIL, 1.0)
            else:
                raw["http_queue"] = None
        except Exception:
            raw["http_queue"] = None

        # — GPU —
        try:
            from lumina.systools.hw_gpu import get_gpu_usage
            result = get_gpu_usage()
            if result is not None:
                snap.gpu_pct = result["vram_pct_used"]
                raw["gpu"] = min(result["vram_pct_used"] / _GPU_CEIL_PCT, 1.0)
            else:
                raw["gpu"] = None
        except Exception:
            raw["gpu"] = None

        # — Weighted score with redistribution —
        snap.load_score = self._compute_score(raw)
        snap.is_idle = snap.load_score < self._idle_threshold

        # — Push into telemetry window —
        self._window.push(snap)
        return snap

    def get_window_summary(self) -> TelemetrySummary:
        """Return the current sliding-window telemetry summary (dual-format)."""
        return self._window.summary()

    @property
    def window(self) -> TelemetryWindow:
        """Direct access to the telemetry window (for daemon status exposure)."""
        return self._window

    # ── Internal ──────────────────────────────────────────────

    def _compute_score(self, raw: dict[str, float | None]) -> float:
        """Compute weighted average, redistributing weight from absent probes."""
        active_weight = 0.0
        weighted_sum = 0.0
        for probe_name, weight in self._weights.items():
            val = raw.get(probe_name)
            if val is not None:
                active_weight += weight
                weighted_sum += weight * val

        if active_weight <= 0.0:
            return 0.0
        return weighted_sum / active_weight

    def configure(self, cfg: dict[str, Any]) -> None:
        """Hot-reload configuration from daemon config dict."""
        if "probe_weights" in cfg:
            self._weights = dict(cfg["probe_weights"])
        if "idle_threshold" in cfg:
            self._idle_threshold = float(cfg["idle_threshold"])
        if "telemetry_window_depth" in cfg:
            new_depth = int(cfg["telemetry_window_depth"])
            if new_depth != self._window.max_depth:
                self._window = TelemetryWindow(max_depth=new_depth)
