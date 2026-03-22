"""Tests for lumina.system_log.event_payload — LogLevel, LogEvent, create_event."""
from __future__ import annotations

import json

import pytest

from lumina.system_log.event_payload import LogEvent, LogLevel, create_event


class TestLogLevel:

    @pytest.mark.unit
    def test_all_members(self) -> None:
        names = {m.name for m in LogLevel}
        assert names == {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "AUDIT"}

    @pytest.mark.unit
    def test_string_value(self) -> None:
        assert LogLevel.AUDIT.value == "AUDIT"
        assert LogLevel.WARNING == "WARNING"

    @pytest.mark.unit
    def test_construct_from_string(self) -> None:
        assert LogLevel("ERROR") is LogLevel.ERROR


class TestLogEvent:

    @pytest.mark.unit
    def test_fields(self) -> None:
        evt = LogEvent(
            timestamp="2025-01-01T00:00:00+00:00",
            source="test",
            level=LogLevel.INFO,
            category="unit_test",
            message="hello",
        )
        assert evt.source == "test"
        assert evt.level is LogLevel.INFO
        assert evt.data == {}
        assert evt.record is None

    @pytest.mark.unit
    def test_frozen(self) -> None:
        evt = create_event("x", LogLevel.DEBUG, "cat", "msg")
        with pytest.raises(AttributeError):
            evt.source = "y"  # type: ignore[misc]

    @pytest.mark.unit
    def test_to_dict(self) -> None:
        evt = create_event("src", LogLevel.AUDIT, "hash_chain", "rec appended", record={"a": 1})
        d = evt.to_dict()
        assert d["level"] == "AUDIT"
        assert d["record"] == {"a": 1}
        assert d["source"] == "src"

    @pytest.mark.unit
    def test_to_dict_json_serialisable(self) -> None:
        evt = create_event("src", "WARNING", "cat", "oops", data={"n": 42})
        text = json.dumps(evt.to_dict())
        assert '"WARNING"' in text


class TestCreateEvent:

    @pytest.mark.unit
    def test_auto_timestamp(self) -> None:
        evt = create_event("s", LogLevel.INFO, "c", "m")
        assert evt.timestamp  # non-empty
        assert "T" in evt.timestamp  # ISO-8601

    @pytest.mark.unit
    def test_string_level_coercion(self) -> None:
        evt = create_event("s", "CRITICAL", "c", "m")
        assert evt.level is LogLevel.CRITICAL

    @pytest.mark.unit
    def test_default_data(self) -> None:
        evt = create_event("s", LogLevel.DEBUG, "c", "m")
        assert evt.data == {}

    @pytest.mark.unit
    def test_with_record(self) -> None:
        rec = {"record_type": "TraceEvent", "record_id": "abc"}
        evt = create_event("s", LogLevel.AUDIT, "hash_chain", "m", record=rec)
        assert evt.record is rec
