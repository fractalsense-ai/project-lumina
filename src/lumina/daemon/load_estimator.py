"""load_estimator.py — Weighted load-score aggregator.

Aggregates the three load probes (event-loop latency, in-flight HTTP
requests, GPU VRAM) into a single 0.0–1.0 ``load_score``.  When a probe
returns ``None`` its weight is redistributed among the remaining probes
so the score degrades gracefully.

Used by ``resource_monitor.ResourceMonitorDaemon`` each poll cycle.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
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

    Parameters
    ----------
    weights:
        Mapping of probe name → weight (must sum to 1.0).
    idle_threshold:
        ``load_score`` below this marks ``is_idle = True``.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        idle_threshold: float = DEFAULT_IDLE_THRESHOLD,
    ) -> None:
        self._weights = dict(weights or DEFAULT_WEIGHTS)
        self._idle_threshold = idle_threshold

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
        return snap

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
