"""Tests for lumina.system_log.alert_store — bounded WarningStore and AlertStore."""
from __future__ import annotations

import pytest

from lumina.system_log.alert_store import AlertStore, WarningStore
from lumina.system_log.event_payload import LogLevel, create_event


def _warn_event(msg: str, cat: str = "test") -> "LogEvent":  # noqa: F821
    return create_event("t", LogLevel.WARNING, cat, msg)


def _error_event(msg: str) -> "LogEvent":  # noqa: F821
    return create_event("t", LogLevel.ERROR, "test", msg)


class TestWarningStore:

    @pytest.mark.unit
    def test_push_and_len(self) -> None:
        ws = WarningStore()
        ws.push(_warn_event("a"))
        ws.push(_warn_event("b"))
        assert len(ws) == 2

    @pytest.mark.unit
    def test_query_most_recent_first(self) -> None:
        ws = WarningStore()
        ws.push(_warn_event("first"))
        ws.push(_warn_event("second"))
        results = ws.query(limit=10)
        assert results[0]["message"] == "second"
        assert results[1]["message"] == "first"

    @pytest.mark.unit
    def test_query_category_filter(self) -> None:
        ws = WarningStore()
        ws.push(_warn_event("a", cat="alpha"))
        ws.push(_warn_event("b", cat="beta"))
        results = ws.query(category_filter="alpha")
        assert len(results) == 1
        assert results[0]["category"] == "alpha"

    @pytest.mark.unit
    def test_query_pagination(self) -> None:
        ws = WarningStore()
        for i in range(5):
            ws.push(_warn_event(f"m{i}"))
        page = ws.query(limit=2, offset=1)
        assert len(page) == 2

    @pytest.mark.unit
    def test_bounded_eviction(self) -> None:
        ws = WarningStore(maxlen=3)
        for i in range(5):
            ws.push(_warn_event(f"m{i}"))
        assert len(ws) == 3
        results = ws.query(limit=10)
        # Most-recent three should survive.
        messages = [r["message"] for r in results]
        assert messages == ["m4", "m3", "m2"]


class TestAlertStore:

    @pytest.mark.unit
    def test_push_and_query(self) -> None:
        a = AlertStore()
        a.push(_error_event("e1"))
        a.push(_error_event("e2"))
        results = a.query()
        assert len(results) == 2
        assert results[0]["message"] == "e2"  # most-recent first

    @pytest.mark.unit
    def test_bounded_eviction(self) -> None:
        a = AlertStore(maxlen=2)
        for i in range(4):
            a.push(_error_event(f"e{i}"))
        assert len(a) == 2
        results = a.query()
        assert [r["message"] for r in results] == ["e3", "e2"]
