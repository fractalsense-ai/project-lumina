"""Tests for lumina.session.blackbox and blackbox_triggers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumina.session.blackbox import (
    BlackBoxSnapshot,
    capture_blackbox,
    write_blackbox,
    _prune_old_snapshots,
)
from lumina.session.blackbox_triggers import TriggerRegistry, trigger_registry
from lumina.session.ring_buffer import ConversationRingBuffer


# ── TriggerRegistry ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_trigger_register_and_check() -> None:
    reg = TriggerRegistry()
    reg.register("high_load", lambda e: e.get("load_score", 0) > 0.8)
    assert "high_load" in reg.registered
    assert reg.check({"load_score": 0.9}) == ["high_load"]
    assert reg.check({"load_score": 0.5}) == []


@pytest.mark.unit
def test_trigger_unregister() -> None:
    reg = TriggerRegistry()
    reg.register("tmp", lambda e: True)
    reg.unregister("tmp")
    assert "tmp" not in reg.registered


@pytest.mark.unit
def test_trigger_exception_handling() -> None:
    """A failing trigger should not crash the check loop."""
    reg = TriggerRegistry()
    reg.register("bad", lambda e: 1 / 0)
    reg.register("good", lambda e: True)
    fired = reg.check({})
    assert "good" in fired
    assert "bad" not in fired


@pytest.mark.unit
def test_builtin_escalation_critical() -> None:
    event = {
        "record_type": "EscalationRecord",
        "trigger": "critical_invariant_violation",
    }
    fired = trigger_registry.check(event)
    assert "escalation_critical" in fired


@pytest.mark.unit
def test_builtin_escalation_severe() -> None:
    event = {
        "record_type": "EscalationRecord",
        "target_role": "meta_authority",
    }
    fired = trigger_registry.check(event)
    assert "escalation_severe" in fired


@pytest.mark.unit
def test_builtin_no_false_positive() -> None:
    event = {"record_type": "TraceEvent", "trigger": "none"}
    fired = trigger_registry.check(event)
    assert fired == []


# ── capture_blackbox ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_capture_blackbox_basic() -> None:
    snap = capture_blackbox(
        session_id="sess-1",
        domain_id="edu",
        trigger_type="escalation_critical",
        trigger_source="escalation",
    )
    assert isinstance(snap, BlackBoxSnapshot)
    assert snap.session_id == "sess-1"
    assert snap.domain_id == "edu"
    assert snap.trigger_type == "escalation_critical"
    assert snap.schema_version == "1.0"


@pytest.mark.unit
def test_capture_with_ring_buffer() -> None:
    rb = ConversationRingBuffer(maxlen=5)
    rb.push("hello", "world", 1, "edu")
    rb.push("question", "answer", 2, "edu")
    snap = capture_blackbox(
        session_id="sess-2",
        domain_id="edu",
        trigger_type="test",
        trigger_source="manual",
        ring_buffer_snapshot=rb.snapshot(),
    )
    assert len(snap.conversation_buffer) == 2
    assert snap.conversation_buffer[0]["user_message"] == "hello"


@pytest.mark.unit
def test_capture_with_telemetry() -> None:
    telem = {"load_trajectory": "rising", "baseline": 0.3}
    snap = capture_blackbox(
        session_id="sess-3",
        domain_id="agri",
        trigger_type="test",
        trigger_source="manual",
        telemetry_summary=telem,
    )
    assert snap.telemetry_window["load_trajectory"] == "rising"


# ── write_blackbox ───────────────────────────────────────────────────────────


@pytest.mark.unit
def test_write_blackbox(tmp_path: Path) -> None:
    snap = capture_blackbox(
        session_id="test-session",
        domain_id="edu",
        trigger_type="test",
        trigger_source="manual",
    )
    out = write_blackbox(snap, output_dir=tmp_path, max_files=100)
    assert out.exists()
    assert out.suffix == ".json"
    data = json.loads(out.read_text())
    assert data["session_id"] == "test-session"
    assert data["schema_version"] == "1.0"


@pytest.mark.unit
def test_write_blackbox_atomic(tmp_path: Path) -> None:
    """After write, no .tmp files should remain."""
    snap = capture_blackbox(
        session_id="atomic-test",
        domain_id="edu",
        trigger_type="test",
        trigger_source="manual",
    )
    write_blackbox(snap, output_dir=tmp_path)
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == []


@pytest.mark.unit
def test_prune_old_snapshots(tmp_path: Path) -> None:
    """Auto-purge should remove oldest files when exceeding max."""
    for i in range(5):
        (tmp_path / f"snap-{i:03d}.json").write_text("{}")
    _prune_old_snapshots(tmp_path, max_files=3)
    remaining = list(tmp_path.glob("*.json"))
    assert len(remaining) == 3


@pytest.mark.unit
def test_write_blackbox_with_full_diagnostic(tmp_path: Path) -> None:
    rb = ConversationRingBuffer(maxlen=5)
    rb.push("q1", "a1", 1, "edu")
    rb.push("q2", "a2", 2, "edu")
    snap = capture_blackbox(
        session_id="full-diag",
        domain_id="edu",
        trigger_type="escalation_severe",
        trigger_source="escalation",
        ring_buffer_snapshot=rb.snapshot(),
        telemetry_summary={"load_trajectory": "spiking", "baseline": 0.4},
        recent_trace_events=[{"record_type": "TraceEvent", "action": "scaffolding"}],
        session_state={"task_id": "task-1", "turn_count": 5},
        system_health={"disk_ok": True, "memory_ok": True},
    )
    out = write_blackbox(snap, output_dir=tmp_path)
    data = json.loads(out.read_text())
    assert len(data["conversation_buffer"]) == 2
    assert data["telemetry_window"]["load_trajectory"] == "spiking"
    assert len(data["trace_events"]) == 1
    assert data["session_state"]["task_id"] == "task-1"
    assert data["system_health"]["disk_ok"] is True
