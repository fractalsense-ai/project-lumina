"""Tests for lumina.lib.system_health and hw_* probes."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from lumina.lib.system_health import (
    DISK_WARN_PCT,
    MEMORY_WARN_PCT,
    TEMP_WARN_C,
    SystemHealthMonitor,
    SystemHealthState,
)


# ── SystemHealthState dataclass ────────────────────────────────────────────────


@pytest.mark.unit
def test_system_health_state_defaults() -> None:
    state = SystemHealthState()
    assert state.disk_ok is True
    assert state.disk_pct_used == 0.0
    assert state.disk_free_gb == 0.0
    assert state.memory_ok is True
    assert state.memory_pct_used == 0.0
    assert state.memory_free_mb == 0.0
    assert state.temp_ok is True
    assert state.temp_c is None
    assert state.errors == []


@pytest.mark.unit
def test_system_health_state_instantiation_with_values() -> None:
    state = SystemHealthState(
        disk_ok=False,
        disk_pct_used=90.0,
        disk_free_gb=5.0,
        memory_ok=True,
        memory_pct_used=50.0,
        memory_free_mb=4096.0,
        temp_ok=False,
        temp_c=80.0,
        errors=["probe failed"],
    )
    assert state.disk_ok is False
    assert state.disk_pct_used == 90.0
    assert state.temp_c == 80.0
    assert "probe failed" in state.errors


# ── SystemHealthMonitor defaults ───────────────────────────────────────────────


@pytest.mark.unit
def test_monitor_default_thresholds() -> None:
    monitor = SystemHealthMonitor()
    assert monitor._disk_warn == DISK_WARN_PCT
    assert monitor._memory_warn == MEMORY_WARN_PCT
    assert monitor._temp_warn == TEMP_WARN_C


@pytest.mark.unit
def test_monitor_custom_thresholds() -> None:
    monitor = SystemHealthMonitor(disk_warn_pct=50.0, memory_warn_pct=60.0, temp_warn_c=65.0)
    assert monitor._disk_warn == 50.0
    assert monitor._memory_warn == 60.0
    assert monitor._temp_warn == 65.0


# ── SystemHealthMonitor.sample — disk probe ───────────────────────────────────


@pytest.mark.unit
def test_sample_disk_ok_when_under_threshold() -> None:
    monitor = SystemHealthMonitor(disk_warn_pct=90.0)
    with patch("lumina.systools.hw_disk.get_disk_usage", return_value={"pct_used": 50.0, "free_gb": 100.0}):
        state = monitor.sample()
    assert state.disk_ok is True
    assert state.disk_pct_used == 50.0
    assert state.disk_free_gb == 100.0


@pytest.mark.unit
def test_sample_disk_not_ok_when_over_threshold() -> None:
    monitor = SystemHealthMonitor(disk_warn_pct=70.0)
    with patch("lumina.systools.hw_disk.get_disk_usage", return_value={"pct_used": 85.0, "free_gb": 10.0}):
        state = monitor.sample()
    assert state.disk_ok is False


@pytest.mark.unit
def test_sample_disk_probe_returns_none() -> None:
    monitor = SystemHealthMonitor()
    with patch("lumina.systools.hw_disk.get_disk_usage", return_value=None):
        state = monitor.sample()
    assert state.disk_ok is True  # unchanged default
    assert state.errors == []


@pytest.mark.unit
def test_sample_disk_probe_raises() -> None:
    monitor = SystemHealthMonitor()
    with patch("lumina.systools.hw_disk.get_disk_usage", side_effect=RuntimeError("probe fail")):
        state = monitor.sample()
    assert len(state.errors) >= 1
    assert "disk probe" in state.errors[0]


# ── SystemHealthMonitor.sample — memory probe ─────────────────────────────────


@pytest.mark.unit
def test_sample_memory_ok_when_under_threshold() -> None:
    monitor = SystemHealthMonitor(memory_warn_pct=90.0)
    with patch("lumina.systools.hw_memory.get_memory_usage", return_value={"pct_used": 60.0, "free_mb": 2048.0}):
        state = monitor.sample()
    assert state.memory_ok is True
    assert state.memory_pct_used == 60.0


@pytest.mark.unit
def test_sample_memory_not_ok_over_threshold() -> None:
    monitor = SystemHealthMonitor(memory_warn_pct=70.0)
    with patch("lumina.systools.hw_memory.get_memory_usage", return_value={"pct_used": 80.0, "free_mb": 512.0}):
        state = monitor.sample()
    assert state.memory_ok is False


@pytest.mark.unit
def test_sample_memory_probe_returns_none() -> None:
    monitor = SystemHealthMonitor()
    with patch("lumina.systools.hw_memory.get_memory_usage", return_value=None):
        state = monitor.sample()
    assert state.memory_ok is True
    assert state.errors == []


@pytest.mark.unit
def test_sample_memory_probe_raises() -> None:
    monitor = SystemHealthMonitor()
    with patch("lumina.systools.hw_memory.get_memory_usage", side_effect=OSError("no mem info")):
        state = monitor.sample()
    assert len(state.errors) >= 1
    assert "memory probe" in state.errors[0]


# ── SystemHealthMonitor.sample — temperature probe ────────────────────────────


@pytest.mark.unit
def test_sample_temp_ok_when_under_threshold() -> None:
    monitor = SystemHealthMonitor(temp_warn_c=80.0)
    with patch("lumina.systools.hw_temp.get_cpu_temp", return_value={"cpu_temp_c": 55.0}):
        state = monitor.sample()
    assert state.temp_ok is True
    assert state.temp_c == 55.0


@pytest.mark.unit
def test_sample_temp_not_ok_over_threshold() -> None:
    monitor = SystemHealthMonitor(temp_warn_c=70.0)
    with patch("lumina.systools.hw_temp.get_cpu_temp", return_value={"cpu_temp_c": 78.0}):
        state = monitor.sample()
    assert state.temp_ok is False


@pytest.mark.unit
def test_sample_temp_probe_returns_none() -> None:
    monitor = SystemHealthMonitor()
    with patch("lumina.systools.hw_temp.get_cpu_temp", return_value=None):
        state = monitor.sample()
    assert state.temp_c is None
    assert state.errors == []


@pytest.mark.unit
def test_sample_temp_cpu_temp_c_is_none() -> None:
    monitor = SystemHealthMonitor()
    with patch("lumina.systools.hw_temp.get_cpu_temp", return_value={"cpu_temp_c": None}):
        state = monitor.sample()
    assert state.temp_c is None
    assert state.temp_ok is True  # Not updated if temp_c is None


@pytest.mark.unit
def test_sample_temp_probe_raises() -> None:
    monitor = SystemHealthMonitor()
    with patch("lumina.systools.hw_temp.get_cpu_temp", side_effect=Exception("sensor error")):
        state = monitor.sample()
    assert len(state.errors) >= 1
    assert "temp probe" in state.errors[0]


# ── All probes together ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_sample_all_stubs_return_none() -> None:
    """With stub hw_* modules that return None, sample() should still return a valid state."""
    monitor = SystemHealthMonitor()
    state = monitor.sample()
    assert isinstance(state, SystemHealthState)
    # Stubs return None so disk/memory/temp stay at defaults
    assert state.disk_ok is True
    assert state.memory_ok is True
    assert state.temp_ok is True


# ── hw_* stub functions ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_hw_disk_stub_returns_none() -> None:
    from lumina.systools.hw_disk import get_disk_usage

    assert get_disk_usage() is None
    assert get_disk_usage("/") is None


@pytest.mark.unit
def test_hw_memory_stub_returns_none() -> None:
    from lumina.systools.hw_memory import get_memory_usage

    assert get_memory_usage() is None


@pytest.mark.unit
def test_hw_temp_stub_returns_none() -> None:
    from lumina.systools.hw_temp import get_cpu_temp

    assert get_cpu_temp() is None
