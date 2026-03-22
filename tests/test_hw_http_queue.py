"""Tests for lumina.systools.hw_http_queue."""
from __future__ import annotations

import threading

import pytest

from lumina.systools.hw_http_queue import (
    decrement,
    get_inflight_requests,
    increment,
    reset,
)


@pytest.fixture(autouse=True)
def _reset_counters() -> None:
    """Reset counters before each test."""
    reset()


# ── Basic operations ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_initial_state() -> None:
    result = get_inflight_requests()
    assert result is not None
    assert result["inflight"] == 0
    assert result["max_seen"] == 0


@pytest.mark.unit
def test_increment_and_get() -> None:
    increment()
    result = get_inflight_requests()
    assert result is not None
    assert result["inflight"] == 1
    assert result["max_seen"] == 1


@pytest.mark.unit
def test_increment_decrement() -> None:
    increment()
    increment()
    decrement()
    result = get_inflight_requests()
    assert result is not None
    assert result["inflight"] == 1
    assert result["max_seen"] == 2


@pytest.mark.unit
def test_decrement_does_not_go_negative() -> None:
    decrement()
    result = get_inflight_requests()
    assert result is not None
    assert result["inflight"] == 0


@pytest.mark.unit
def test_max_seen_tracks_peak() -> None:
    for _ in range(5):
        increment()
    for _ in range(5):
        decrement()
    result = get_inflight_requests()
    assert result is not None
    assert result["inflight"] == 0
    assert result["max_seen"] == 5


# ── Thread safety ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_concurrent_increments() -> None:
    threads = []
    for _ in range(100):
        t = threading.Thread(target=increment)
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    result = get_inflight_requests()
    assert result is not None
    assert result["inflight"] == 100
    assert result["max_seen"] == 100
